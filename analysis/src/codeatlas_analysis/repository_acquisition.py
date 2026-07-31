from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import PurePosixPath
from stat import S_ISLNK
from zipfile import BadZipFile, ZipFile, ZipInfo

from codeatlas_analysis.repository_intake import RepositoryIdentity

_SUPPORTED_SUFFIXES = {".cjs", ".js", ".json", ".jsx", ".mjs", ".ts", ".tsx"}


class AcquisitionErrorCode(StrEnum):
    INVALID_ARCHIVE = "invalid_archive"
    UNSAFE_ARCHIVE_PATH = "unsafe_archive_path"
    ARCHIVE_LIMIT_EXCEEDED = "archive_limit_exceeded"
    INVALID_SOURCE_ENCODING = "invalid_source_encoding"
    INVALID_SOURCE_RESPONSE = "invalid_source_response"
    SOURCE_UNAVAILABLE = "source_unavailable"


class RepositoryAcquisitionError(ValueError):
    def __init__(self, code: AcquisitionErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class AcquisitionLimits:
    max_archive_bytes: int = 20 * 1024 * 1024
    max_entries: int = 10_000
    max_files: int = 5_000
    max_uncompressed_bytes: int = 50 * 1024 * 1024
    max_file_bytes: int = 512 * 1024
    max_path_depth: int = 20
    request_timeout_seconds: float = 10.0


_DEFAULT_LIMITS = AcquisitionLimits()


@dataclass(frozen=True, slots=True)
class RepositoryFile:
    path: str
    content: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    repository: RepositoryIdentity
    revision: str
    files: tuple[RepositoryFile, ...]


def _reject(code: AcquisitionErrorCode, message: str) -> None:
    raise RepositoryAcquisitionError(code, message)


def _archive_path(entry: ZipInfo) -> tuple[str, PurePosixPath] | None:
    raw_parts = entry.filename.split("/")
    if (
        entry.filename.startswith("/")
        or "\\" in entry.filename
        or any(part in {"", ".", ".."} for part in raw_parts[:-1])
    ):
        _reject(
            AcquisitionErrorCode.UNSAFE_ARCHIVE_PATH,
            "Repository archive contains an unsafe path.",
        )
    if entry.is_dir():
        return None
    if not raw_parts or not raw_parts[-1] or len(raw_parts) < 2:
        _reject(
            AcquisitionErrorCode.INVALID_ARCHIVE,
            "Repository archive must contain one root directory.",
        )
    return raw_parts[0], PurePosixPath(*raw_parts[1:])


def _read_source_file(
    archive: ZipFile,
    entry: ZipInfo,
    relative: PurePosixPath,
    limits: AcquisitionLimits,
) -> RepositoryFile:
    if entry.file_size > limits.max_file_bytes:
        _reject(
            AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED,
            "Repository source file exceeds the file-size limit.",
        )
    with archive.open(entry) as source:
        content_bytes = source.read(limits.max_file_bytes + 1)
    if len(content_bytes) > limits.max_file_bytes:
        _reject(
            AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED,
            "Repository source file exceeds the file-size limit.",
        )
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RepositoryAcquisitionError(
            AcquisitionErrorCode.INVALID_SOURCE_ENCODING,
            "Repository source files must use UTF-8 encoding.",
        ) from error
    return RepositoryFile(
        path=relative.as_posix(),
        content=content,
        size_bytes=len(content_bytes),
    )


def _validate_archive_limits(entries: list[ZipInfo], limits: AcquisitionLimits) -> None:
    if len(entries) > limits.max_entries:
        _reject(
            AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED,
            "Repository archive exceeds the entry-count limit.",
        )
    if sum(entry.file_size for entry in entries) > limits.max_uncompressed_bytes:
        _reject(
            AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED,
            "Repository archive exceeds the uncompressed-size limit.",
        )


def _source_entries(
    entries: list[ZipInfo], limits: AcquisitionLimits
) -> list[tuple[ZipInfo, PurePosixPath]]:
    roots: set[str] = set()
    seen_paths: set[str] = set()
    selected: list[tuple[ZipInfo, PurePosixPath]] = []
    for entry in entries:
        parsed_path = _archive_path(entry)
        if parsed_path is None:
            continue
        root, relative = parsed_path
        roots.add(root)
        if len(relative.parts) > limits.max_path_depth:
            _reject(
                AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED,
                "Repository source path exceeds the depth limit.",
            )
        if S_ISLNK(entry.external_attr >> 16) or relative.suffix.lower() not in _SUPPORTED_SUFFIXES:
            continue
        path = relative.as_posix()
        if path in seen_paths:
            _reject(
                AcquisitionErrorCode.INVALID_ARCHIVE,
                "Repository archive contains duplicate source paths.",
            )
        seen_paths.add(path)
        selected.append((entry, relative))
        if len(selected) > limits.max_files:
            _reject(
                AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED,
                "Repository archive exceeds the source-file limit.",
            )
    if len(roots) != 1:
        _reject(
            AcquisitionErrorCode.INVALID_ARCHIVE,
            "Repository archive must contain one root directory.",
        )
    return selected


def read_repository_zip(
    *,
    repository: RepositoryIdentity,
    revision: str,
    archive_bytes: bytes,
    limits: AcquisitionLimits = _DEFAULT_LIMITS,
) -> RepositorySnapshot:
    if len(archive_bytes) > limits.max_archive_bytes:
        _reject(
            AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED,
            "Repository archive exceeds the download limit.",
        )

    try:
        with ZipFile(BytesIO(archive_bytes)) as archive:
            entries = archive.infolist()
            _validate_archive_limits(entries, limits)
            files = [
                _read_source_file(archive, entry, relative, limits)
                for entry, relative in _source_entries(entries, limits)
            ]
    except BadZipFile as error:
        raise RepositoryAcquisitionError(
            AcquisitionErrorCode.INVALID_ARCHIVE,
            "Repository archive is not a valid ZIP file.",
        ) from error

    return RepositorySnapshot(
        repository=repository,
        revision=revision,
        files=tuple(sorted(files, key=lambda file: file.path)),
    )
