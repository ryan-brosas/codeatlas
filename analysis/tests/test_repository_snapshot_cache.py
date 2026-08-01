import pytest

from codeatlas_analysis.repository_acquisition import RepositoryFile, RepositorySnapshot
from codeatlas_analysis.repository_intake import normalize_public_github_repository


def _snapshot(name: str, revision: str, size: int) -> RepositorySnapshot:
    repository = normalize_public_github_repository(f"https://github.com/example/{name}")
    return RepositorySnapshot(
        repository=repository,
        revision=revision,
        files=(RepositoryFile(path="index.ts", content="x" * size, size_bytes=size),),
    )


def test_returns_snapshot_until_fixed_ttl_expires() -> None:
    from codeatlas_analysis.repository_snapshot_cache import (
        InMemoryRepositorySnapshotCache,
    )

    now = 0.0
    cache = InMemoryRepositorySnapshotCache(
        max_entries=2,
        max_source_bytes=10,
        ttl_seconds=5.0,
        now=lambda: now,
    )
    snapshot = _snapshot("project", "a" * 40, 3)

    cache.put(snapshot)
    assert cache.get(snapshot.repository.id, snapshot.revision) == snapshot

    now = 5.0
    assert cache.get(snapshot.repository.id, snapshot.revision) is None


def test_evicts_least_recent_snapshot_at_capacity() -> None:
    from codeatlas_analysis.repository_snapshot_cache import (
        InMemoryRepositorySnapshotCache,
    )

    cache = InMemoryRepositorySnapshotCache(
        max_entries=2,
        max_source_bytes=10,
        ttl_seconds=60.0,
    )
    first = _snapshot("first", "a" * 40, 3)
    second = _snapshot("second", "b" * 40, 3)
    third = _snapshot("third", "c" * 40, 3)

    cache.put(first)
    cache.put(second)
    assert cache.get(first.repository.id, first.revision) == first
    cache.put(third)

    assert cache.get(first.repository.id, first.revision) == first
    assert cache.get(second.repository.id, second.revision) is None
    assert cache.get(third.repository.id, third.revision) == third


def test_enforces_source_byte_budget_and_skips_oversized_snapshot() -> None:
    from codeatlas_analysis.repository_snapshot_cache import (
        InMemoryRepositorySnapshotCache,
    )

    cache = InMemoryRepositorySnapshotCache(
        max_entries=3,
        max_source_bytes=5,
        ttl_seconds=60.0,
    )
    first = _snapshot("first", "a" * 40, 3)
    second = _snapshot("second", "b" * 40, 3)
    oversized = _snapshot("oversized", "c" * 40, 6)

    cache.put(first)
    cache.put(second)
    cache.put(oversized)

    assert cache.get(first.repository.id, first.revision) is None
    assert cache.get(second.repository.id, second.revision) == second
    assert cache.get(oversized.repository.id, oversized.revision) is None


@pytest.mark.parametrize(
    ("max_entries", "max_source_bytes", "ttl_seconds"),
    [(0, 1, 1.0), (1, 0, 1.0), (1, 1, 0.0)],
)
def test_rejects_non_positive_limits(
    max_entries: int, max_source_bytes: int, ttl_seconds: float
) -> None:
    from codeatlas_analysis.repository_snapshot_cache import (
        InMemoryRepositorySnapshotCache,
    )

    with pytest.raises(ValueError, match="positive"):
        InMemoryRepositorySnapshotCache(
            max_entries=max_entries,
            max_source_bytes=max_source_bytes,
            ttl_seconds=ttl_seconds,
        )
