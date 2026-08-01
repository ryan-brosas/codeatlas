import json
from collections.abc import Mapping
from io import BytesIO
from types import TracebackType
from typing import Self
from urllib.request import Request
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from codeatlas_analysis.github_repository_source import (
    GitHubArchiveSource,
    UrlLibHttpTransport,
)
from codeatlas_analysis.repository_acquisition import (
    AcquisitionErrorCode,
    RepositoryAcquisitionError,
)
from codeatlas_analysis.repository_intake import normalize_public_github_repository


class RecordingTransport:
    def __init__(self, responses: list[bytes]) -> None:
        self._responses = iter(responses)
        self.requests: list[tuple[str, int, float]] = []

    def get(
        self,
        url: str,
        *,
        max_bytes: int,
        timeout_seconds: float,
    ) -> bytes:
        self.requests.append((url, max_bytes, timeout_seconds))
        return next(self._responses)


def _zip_source() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("example-project-revision/src/index.ts", b"export {};\n")
    return buffer.getvalue()


def test_reuses_cached_archive_after_resolving_the_same_revision() -> None:
    from codeatlas_analysis.repository_snapshot_cache import (
        InMemoryRepositorySnapshotCache,
    )

    revision = "0123456789abcdef0123456789abcdef01234567"
    commit = json.dumps([{"sha": revision}]).encode()
    transport = RecordingTransport([commit, _zip_source(), commit])
    cache = InMemoryRepositorySnapshotCache(
        max_entries=2,
        max_source_bytes=1024,
        ttl_seconds=60.0,
    )
    repository = normalize_public_github_repository("https://github.com/example/project")
    source = GitHubArchiveSource(transport, cache=cache)

    first = source.acquire(repository)
    second = source.acquire(repository)

    assert second is first
    assert [url for url, _max_bytes, _timeout in transport.requests] == [
        "https://api.github.com/repos/example/project/commits?per_page=1",
        f"https://api.github.com/repos/example/project/zipball/{revision}",
        "https://api.github.com/repos/example/project/commits?per_page=1",
    ]


def test_acquires_a_commit_pinned_github_archive() -> None:
    revision = "0123456789abcdef0123456789abcdef01234567"
    transport = RecordingTransport([json.dumps([{"sha": revision}]).encode(), _zip_source()])
    repository = normalize_public_github_repository("https://github.com/example/project")

    snapshot = GitHubArchiveSource(transport).acquire(repository)

    assert snapshot.repository == repository
    assert snapshot.revision == revision
    assert [file.path for file in snapshot.files] == ["src/index.ts"]
    assert transport.requests == [
        (
            "https://api.github.com/repos/example/project/commits?per_page=1",
            262_144,
            10.0,
        ),
        (
            f"https://api.github.com/repos/example/project/zipball/{revision}",
            20 * 1024 * 1024,
            10.0,
        ),
    ]


@pytest.mark.parametrize(
    "commit_response",
    [
        b"not-json",
        b"[]",
        b'[{"sha": "not-a-commit"}]',
    ],
)
def test_rejects_invalid_github_revision_responses(commit_response: bytes) -> None:
    transport = RecordingTransport([commit_response])

    with pytest.raises(RepositoryAcquisitionError) as raised:
        GitHubArchiveSource(transport).acquire(
            normalize_public_github_repository("https://github.com/example/project")
        )

    assert type(raised.value.code) is AcquisitionErrorCode
    assert raised.value.code.value == "invalid_source_response"
    assert len(transport.requests) == 1


class FakeHttpResponse:
    def __init__(
        self,
        body: bytes,
        *,
        final_url: str = "https://codeload.github.com/example/project/legacy.zip/revision",
        content_length: str | None = None,
    ) -> None:
        self._body = body
        self._final_url = final_url
        self.headers: Mapping[str, str] = (
            {} if content_length is None else {"Content-Length": content_length}
        )

    def read(self, amount: int = -1) -> bytes:
        return self._body if amount < 0 else self._body[:amount]

    def geturl(self) -> str:
        return self._final_url

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


def test_http_transport_bounds_github_https_responses() -> None:
    response = FakeHttpResponse(b"archive", content_length="7")
    requests: list[tuple[Request, float]] = []

    def open_request(request: Request, timeout: float) -> FakeHttpResponse:
        requests.append((request, timeout))
        return response

    content = UrlLibHttpTransport(open_request).get(
        "https://api.github.com/repos/example/project/zipball/revision",
        max_bytes=7,
        timeout_seconds=4.0,
    )

    assert content == b"archive"
    assert requests[0][0].full_url.startswith("https://api.github.com/")
    assert requests[0][0].get_header("User-agent") == "CodeAtlas/0.1"
    assert requests[0][1] == 4.0


@pytest.mark.parametrize(
    "response",
    [
        FakeHttpResponse(b"12345", content_length="5"),
        FakeHttpResponse(b"12345"),
    ],
)
def test_http_transport_rejects_oversized_responses(
    response: FakeHttpResponse,
) -> None:
    transport = UrlLibHttpTransport(lambda _request, _timeout: response)

    with pytest.raises(RepositoryAcquisitionError) as raised:
        transport.get(
            "https://api.github.com/repos/example/project/zipball/revision",
            max_bytes=4,
            timeout_seconds=4.0,
        )

    assert raised.value.code is AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED


def test_http_transport_rejects_untrusted_final_hosts() -> None:
    response = FakeHttpResponse(b"archive", final_url="https://example.com/archive.zip")
    transport = UrlLibHttpTransport(lambda _request, _timeout: response)

    with pytest.raises(RepositoryAcquisitionError) as raised:
        transport.get(
            "https://api.github.com/repos/example/project/zipball/revision",
            max_bytes=20,
            timeout_seconds=4.0,
        )

    assert raised.value.code is AcquisitionErrorCode.INVALID_SOURCE_RESPONSE


def test_records_revision_and_archive_durations_without_repository_labels() -> None:
    from codeatlas_analysis.analysis_telemetry import (
        AnalysisDuration,
        InMemoryAnalysisTelemetry,
    )

    revision = "0123456789abcdef0123456789abcdef01234567"
    transport = RecordingTransport([json.dumps([{"sha": revision}]).encode(), _zip_source()])
    telemetry = InMemoryAnalysisTelemetry()
    clock = iter((0.0, 0.1, 0.1, 0.5))
    source = GitHubArchiveSource(
        transport,
        observer=telemetry,
        now=lambda: next(clock),
    )

    source.acquire(normalize_public_github_repository("https://github.com/example/project"))

    assert [
        (item.metric, item.samples, item.total_seconds, item.max_seconds)
        for item in telemetry.snapshot().durations
    ] == [
        (AnalysisDuration.ARCHIVE_DOWNLOAD_SECONDS, 1, 0.4, 0.4),
        (AnalysisDuration.REVISION_LOOKUP_SECONDS, 1, 0.1, 0.1),
    ]
