from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from threading import Lock
from typing import Protocol


class AnalysisCounter(StrEnum):
    CACHE_EVICTION = "cache_eviction"
    CACHE_EXPIRATION = "cache_expiration"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_SKIP = "cache_skip"


class AnalysisDuration(StrEnum):
    ANALYSIS_SECONDS = "analysis_seconds"
    ARCHIVE_DOWNLOAD_SECONDS = "archive_download_seconds"
    REVISION_LOOKUP_SECONDS = "revision_lookup_seconds"


class AnalysisObserver(Protocol):
    def increment(self, metric: AnalysisCounter, count: int = 1) -> None: ...

    def observe(self, metric: AnalysisDuration, duration_seconds: float) -> None: ...


class NullAnalysisObserver:
    def increment(self, metric: AnalysisCounter, count: int = 1) -> None:
        return None

    def observe(self, metric: AnalysisDuration, duration_seconds: float) -> None:
        return None


@dataclass(frozen=True, slots=True)
class CounterValue:
    metric: AnalysisCounter
    count: int


@dataclass(frozen=True, slots=True)
class DurationValue:
    metric: AnalysisDuration
    samples: int
    total_seconds: float
    max_seconds: float


@dataclass(frozen=True, slots=True)
class AnalysisTelemetrySnapshot:
    counts: tuple[CounterValue, ...]
    durations: tuple[DurationValue, ...]


@dataclass(slots=True)
class _MutableDuration:
    samples: int = 0
    total_seconds: float = 0.0
    max_seconds: float = 0.0


class InMemoryAnalysisTelemetry:
    def __init__(self) -> None:
        self._counts = {metric: 0 for metric in AnalysisCounter}
        self._durations = {metric: _MutableDuration() for metric in AnalysisDuration}
        self._lock = Lock()

    def increment(self, metric: AnalysisCounter, count: int = 1) -> None:
        if count < 1:
            raise ValueError("Telemetry counter increments must be positive.")
        with self._lock:
            self._counts[metric] += count

    def observe(self, metric: AnalysisDuration, duration_seconds: float) -> None:
        if not isfinite(duration_seconds) or duration_seconds < 0:
            raise ValueError("Telemetry durations must be finite and non-negative.")
        with self._lock:
            aggregate = self._durations[metric]
            aggregate.samples += 1
            aggregate.total_seconds += duration_seconds
            aggregate.max_seconds = max(aggregate.max_seconds, duration_seconds)

    def snapshot(self) -> AnalysisTelemetrySnapshot:
        with self._lock:
            return AnalysisTelemetrySnapshot(
                counts=tuple(
                    CounterValue(metric=metric, count=count)
                    for metric, count in self._counts.items()
                    if count
                ),
                durations=tuple(
                    DurationValue(
                        metric=metric,
                        samples=value.samples,
                        total_seconds=value.total_seconds,
                        max_seconds=value.max_seconds,
                    )
                    for metric, value in self._durations.items()
                    if value.samples
                ),
            )
