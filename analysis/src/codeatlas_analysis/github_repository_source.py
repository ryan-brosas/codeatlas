import json
import re
from collections.abc import Callable, Mapping
from http.client import HTTPMessage
from types import TracebackType
from typing import IO, Protocol, Self, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from codeatlas_analysis.repository_acquisition import (
    AcquisitionErrorCode,
    AcquisitionLimits,
    RepositoryAcquisitionError,
    RepositorySnapshot,
    read_repository_zip,
)
from codeatlas_analysis.repository_intake import RepositoryIdentity
from codeatlas_analysis.repository_snapshot_cache import RepositorySnapshotCache

_MAX_COMMIT_RESPONSE_BYTES = 256 * 1024
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_GITHUB_HOSTS = {"api.github.com", "codeload.github.com"}


class HttpResponse(Protocol):
    headers: Mapping[str, str]

    def read(self, amount: int = -1) -> bytes: ...

    def geturl(self) -> str: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


OpenRequest = Callable[[Request, float], HttpResponse]


class HttpTransport(Protocol):
    def get(
        self,
        url: str,
        *,
        max_bytes: int,
        timeout_seconds: float,
    ) -> bytes: ...


def _validate_github_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as error:
        raise RepositoryAcquisitionError(
            AcquisitionErrorCode.INVALID_SOURCE_RESPONSE,
            "GitHub returned an invalid source URL.",
        ) from error
    if (
        parsed.scheme != "https"
        or parsed.hostname not in _ALLOWED_GITHUB_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.netloc != parsed.hostname
    ):
        raise RepositoryAcquisitionError(
            AcquisitionErrorCode.INVALID_SOURCE_RESPONSE,
            "GitHub returned an untrusted source URL.",
        )


class _GitHubRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> Request | None:
        _validate_github_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_GITHUB_OPENER = build_opener(_GitHubRedirectHandler())


def _open_github_request(request: Request, timeout: float) -> HttpResponse:
    return cast(HttpResponse, _GITHUB_OPENER.open(request, timeout=timeout))


class UrlLibHttpTransport:
    def __init__(self, open_request: OpenRequest = _open_github_request) -> None:
        self._open_request = open_request

    def get(
        self,
        url: str,
        *,
        max_bytes: int,
        timeout_seconds: float,
    ) -> bytes:
        _validate_github_url(url)
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "CodeAtlas/0.1",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with self._open_request(request, timeout_seconds) as response:
                _validate_github_url(response.geturl())
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        declared_size = int(content_length)
                    except ValueError as error:
                        raise RepositoryAcquisitionError(
                            AcquisitionErrorCode.INVALID_SOURCE_RESPONSE,
                            "GitHub returned an invalid content length.",
                        ) from error
                    if declared_size < 0:
                        raise RepositoryAcquisitionError(
                            AcquisitionErrorCode.INVALID_SOURCE_RESPONSE,
                            "GitHub returned an invalid content length.",
                        )
                    if declared_size > max_bytes:
                        raise RepositoryAcquisitionError(
                            AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED,
                            "GitHub response exceeds the download limit.",
                        )
                content = response.read(max_bytes + 1)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RepositoryAcquisitionError(
                AcquisitionErrorCode.SOURCE_UNAVAILABLE,
                "GitHub source is unavailable.",
            ) from error
        if len(content) > max_bytes:
            raise RepositoryAcquisitionError(
                AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED,
                "GitHub response exceeds the download limit.",
            )
        return content


class GitHubArchiveSource:
    def __init__(
        self,
        transport: HttpTransport,
        limits: AcquisitionLimits | None = None,
        cache: RepositorySnapshotCache | None = None,
    ) -> None:
        self._transport = transport
        self._limits = limits or AcquisitionLimits()
        self._cache = cache

    def acquire(self, repository: RepositoryIdentity) -> RepositorySnapshot:
        owner = quote(repository.owner, safe="")
        name = quote(repository.name, safe="")
        api_root = f"https://api.github.com/repos/{owner}/{name}"
        commit_response = self._transport.get(
            f"{api_root}/commits?per_page=1",
            max_bytes=_MAX_COMMIT_RESPONSE_BYTES,
            timeout_seconds=self._limits.request_timeout_seconds,
        )
        try:
            commits = json.loads(commit_response)
            revision = commits[0]["sha"]
        except (IndexError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise RepositoryAcquisitionError(
                AcquisitionErrorCode.INVALID_SOURCE_RESPONSE,
                "GitHub did not return a repository revision.",
            ) from error
        if not isinstance(revision, str) or _COMMIT_SHA.fullmatch(revision) is None:
            raise RepositoryAcquisitionError(
                AcquisitionErrorCode.INVALID_SOURCE_RESPONSE,
                "GitHub returned an invalid repository revision.",
            )

        if self._cache is not None:
            cached = self._cache.get(repository.id, revision)
            if cached is not None:
                return cached

        archive_bytes = self._transport.get(
            f"{api_root}/zipball/{revision}",
            max_bytes=self._limits.max_archive_bytes,
            timeout_seconds=self._limits.request_timeout_seconds,
        )
        snapshot = read_repository_zip(
            repository=repository,
            revision=revision,
            archive_bytes=archive_bytes,
            limits=self._limits,
        )
        if self._cache is not None:
            self._cache.put(snapshot)
        return snapshot
