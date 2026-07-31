from io import BytesIO
from stat import S_IFLNK
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from codeatlas_analysis.repository_acquisition import (
    AcquisitionErrorCode,
    AcquisitionLimits,
    RepositoryAcquisitionError,
    read_repository_zip,
)
from codeatlas_analysis.repository_intake import (
    RepositoryIdentity,
    normalize_public_github_repository,
)


def _zip(entries: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def test_reads_supported_source_files_from_a_github_zip_snapshot() -> None:
    repository = normalize_public_github_repository("https://github.com/example/project")
    archive_bytes = _zip(
        {
            "example-project-a1b2c3d/src/index.ts": b"export const answer = 42;\n",
            "example-project-a1b2c3d/src/view.tsx": b"export function View() {}\n",
            "example-project-a1b2c3d/package.json": b'{"name": "project"}\n',
            "example-project-a1b2c3d/assets/logo.png": b"not source",
        }
    )

    snapshot = read_repository_zip(
        repository=repository,
        revision="a1b2c3d",
        archive_bytes=archive_bytes,
    )

    assert snapshot.repository == repository
    assert snapshot.revision == "a1b2c3d"
    assert [(file.path, file.content) for file in snapshot.files] == [
        ("package.json", '{"name": "project"}\n'),
        ("src/index.ts", "export const answer = 42;\n"),
        ("src/view.tsx", "export function View() {}\n"),
    ]


def _repository() -> RepositoryIdentity:
    return normalize_public_github_repository("https://github.com/example/project")


def _acquisition_error(
    entries: dict[str, bytes],
    *,
    limits: AcquisitionLimits | None = None,
) -> RepositoryAcquisitionError:
    with pytest.raises(RepositoryAcquisitionError) as raised:
        read_repository_zip(
            repository=_repository(),
            revision="a1b2c3d",
            archive_bytes=_zip(entries),
            limits=limits or AcquisitionLimits(),
        )
    return raised.value


@pytest.mark.parametrize(
    ("entries", "limits"),
    [
        (
            {"root/a.ts": b"a", "root/b.png": b"b"},
            AcquisitionLimits(max_entries=1),
        ),
        (
            {"root/a.ts": b"a", "root/b.ts": b"b"},
            AcquisitionLimits(max_files=1),
        ),
        (
            {"root/image.png": b"1234"},
            AcquisitionLimits(max_uncompressed_bytes=3),
        ),
        (
            {"root/source.ts": b"1234"},
            AcquisitionLimits(max_file_bytes=3),
        ),
        (
            {"root/a/b/source.ts": b"a"},
            AcquisitionLimits(max_path_depth=2),
        ),
    ],
)
def test_rejects_archives_that_exceed_declared_limits(
    entries: dict[str, bytes],
    limits: AcquisitionLimits,
) -> None:
    error = _acquisition_error(entries, limits=limits)

    assert error.code is AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED


@pytest.mark.parametrize(
    "path",
    [
        "root/../secret.ts",
        "root/src\\secret.ts",
        "/root/secret.ts",
    ],
)
def test_rejects_unsafe_archive_paths(path: str) -> None:
    error = _acquisition_error({path: b"export {};\n"})

    assert error.code is AcquisitionErrorCode.UNSAFE_ARCHIVE_PATH


def test_rejects_non_utf8_source() -> None:
    error = _acquisition_error({"root/source.ts": b"\xff"})

    assert error.code is AcquisitionErrorCode.INVALID_SOURCE_ENCODING


def test_rejects_duplicate_normalized_source_paths() -> None:
    buffer = BytesIO()
    with (
        pytest.warns(UserWarning, match="Duplicate name"),
        ZipFile(buffer, "w", ZIP_DEFLATED) as archive,
    ):
        archive.writestr("root/source.ts", b"first")
        archive.writestr("root/source.ts", b"second")

    with pytest.raises(RepositoryAcquisitionError) as raised:
        read_repository_zip(
            repository=_repository(),
            revision="a1b2c3d",
            archive_bytes=buffer.getvalue(),
        )

    assert raised.value.code is AcquisitionErrorCode.INVALID_ARCHIVE


def test_ignores_symbolic_links_in_source_archives() -> None:
    buffer = BytesIO()
    link = ZipInfo("root/linked.ts")
    link.create_system = 3
    link.external_attr = (S_IFLNK | 0o777) << 16
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(link, b"../outside.ts")

    snapshot = read_repository_zip(
        repository=_repository(),
        revision="a1b2c3d",
        archive_bytes=buffer.getvalue(),
    )

    assert snapshot.files == ()
