from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite
from threading import Lock
from time import monotonic
from typing import Protocol

from codeatlas_analysis.repository_acquisition import RepositorySnapshot

SnapshotKey = tuple[str, str]


class RepositorySnapshotCache(Protocol):
    def get(self, repository_id: str, revision: str) -> RepositorySnapshot | None: ...

    def put(self, snapshot: RepositorySnapshot) -> None: ...


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    snapshot: RepositorySnapshot
    source_bytes: int
    expires_at: float


class InMemoryRepositorySnapshotCache:
    def __init__(
        self,
        *,
        max_entries: int,
        max_source_bytes: int,
        ttl_seconds: float,
        now: Callable[[], float] = monotonic,
    ) -> None:
        if max_entries < 1 or max_source_bytes < 1 or not isfinite(ttl_seconds) or ttl_seconds <= 0:
            raise ValueError("Snapshot cache limits must be positive.")
        self._max_entries = max_entries
        self._max_source_bytes = max_source_bytes
        self._ttl_seconds = ttl_seconds
        self._now = now
        self._entries: OrderedDict[SnapshotKey, _CacheEntry] = OrderedDict()
        self._source_bytes = 0
        self._lock = Lock()

    def get(self, repository_id: str, revision: str) -> RepositorySnapshot | None:
        with self._lock:
            self._prune(self._now())
            key = (repository_id, revision)
            entry = self._entries.get(key)
            if entry is None:
                return None
            self._entries.move_to_end(key)
            return entry.snapshot

    def put(self, snapshot: RepositorySnapshot) -> None:
        source_bytes = sum(file.size_bytes for file in snapshot.files)
        key = (snapshot.repository.id, snapshot.revision)
        with self._lock:
            now = self._now()
            self._prune(now)
            replaced = self._entries.pop(key, None)
            if replaced is not None:
                self._source_bytes -= replaced.source_bytes
            if source_bytes > self._max_source_bytes:
                return
            while self._entries and (
                len(self._entries) >= self._max_entries
                or self._source_bytes + source_bytes > self._max_source_bytes
            ):
                _, evicted = self._entries.popitem(last=False)
                self._source_bytes -= evicted.source_bytes
            self._entries[key] = _CacheEntry(
                snapshot=snapshot,
                source_bytes=source_bytes,
                expires_at=now + self._ttl_seconds,
            )
            self._source_bytes += source_bytes

    def _prune(self, now: float) -> None:
        expired = [key for key, entry in self._entries.items() if entry.expires_at <= now]
        for key in expired:
            entry = self._entries.pop(key)
            self._source_bytes -= entry.source_bytes
