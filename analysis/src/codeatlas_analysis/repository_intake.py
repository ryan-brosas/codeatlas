import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

_ASCII_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_REPOSITORY_SEGMENT = re.compile(r"^[A-Za-z0-9_.-]+$")


class RepositoryStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class RepositoryErrorCode(StrEnum):
    INVALID_URL = "invalid_repository_url"
    UNSUPPORTED_SCHEME = "unsupported_repository_scheme"
    UNSUPPORTED_HOST = "unsupported_repository_host"
    UNSAFE_URL = "unsafe_repository_url"
    INVALID_PATH = "invalid_repository_path"


class RepositoryUrlError(ValueError):
    def __init__(self, code: RepositoryErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class RepositoryIdentity:
    id: str
    host: str
    owner: str
    name: str
    canonical_url: str


@dataclass(frozen=True, slots=True)
class RepositoryRecord:
    repository: RepositoryIdentity
    status: RepositoryStatus


def _reject(code: RepositoryErrorCode, message: str) -> None:
    raise RepositoryUrlError(code, message)


def _valid_repository_segment(value: str) -> bool:
    return value not in {".", ".."} and _REPOSITORY_SEGMENT.fullmatch(value) is not None


def normalize_public_github_repository(repository_url: str) -> RepositoryIdentity:
    if _ASCII_CONTROL.search(repository_url):
        _reject(RepositoryErrorCode.INVALID_URL, "Provide a valid absolute repository URL.")
    raw_url = repository_url.strip()
    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        _reject(RepositoryErrorCode.INVALID_URL, "Provide a valid absolute repository URL.")

    if not parsed.scheme or not parsed.netloc:
        _reject(RepositoryErrorCode.INVALID_URL, "Provide a valid absolute repository URL.")
    if parsed.scheme.lower() != "https":
        _reject(RepositoryErrorCode.UNSUPPORTED_SCHEME, "Repository URLs must use HTTPS.")
    if parsed.hostname is None or parsed.hostname.lower() not in {
        "github.com",
        "www.github.com",
    }:
        _reject(
            RepositoryErrorCode.UNSUPPORTED_HOST,
            "Only public GitHub repositories are supported.",
        )

    if (
        parsed.netloc.lower() not in {"github.com", "www.github.com"}
        or parsed.query
        or parsed.fragment
    ):
        _reject(
            RepositoryErrorCode.UNSAFE_URL,
            "Repository URLs cannot include credentials, ports, queries, or fragments.",
        )

    path_parts = parsed.path.removesuffix("/").split("/")
    if len(path_parts) != 3 or path_parts[0] or not all(path_parts[1:]):
        _reject(
            RepositoryErrorCode.INVALID_PATH,
            "Repository URLs must identify exactly one owner and repository.",
        )
    _, owner, name = path_parts
    name = name.removesuffix(".git")
    if not _valid_repository_segment(owner) or not _valid_repository_segment(name):
        _reject(
            RepositoryErrorCode.INVALID_PATH,
            "Repository owner and name contain unsupported characters.",
        )

    owner = owner.lower()
    name = name.lower()
    repository_id = f"github.com/{owner}/{name}"
    return RepositoryIdentity(
        id=repository_id,
        host="github.com",
        owner=owner,
        name=name,
        canonical_url=f"https://{repository_id}",
    )


class InMemoryRepositoryIntake:
    def __init__(self) -> None:
        self._records: dict[str, RepositoryRecord] = {}

    def submit(self, repository_url: str) -> RepositoryRecord:
        repository = normalize_public_github_repository(repository_url)
        record = RepositoryRecord(repository=repository, status=RepositoryStatus.PENDING)
        return self._records.setdefault(repository.id, record)
