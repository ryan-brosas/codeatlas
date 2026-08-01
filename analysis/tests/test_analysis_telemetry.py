import math

import pytest


def test_aggregates_only_fixed_metric_names() -> None:
    from codeatlas_analysis.analysis_telemetry import (
        AnalysisCounter,
        AnalysisDuration,
        InMemoryAnalysisTelemetry,
    )

    telemetry = InMemoryAnalysisTelemetry()
    telemetry.increment(AnalysisCounter.CACHE_HIT)
    telemetry.increment(AnalysisCounter.CACHE_HIT, 2)
    telemetry.increment(AnalysisCounter.CACHE_MISS)
    telemetry.observe(AnalysisDuration.REVISION_LOOKUP_SECONDS, 0.1)
    telemetry.observe(AnalysisDuration.REVISION_LOOKUP_SECONDS, 0.3)

    snapshot = telemetry.snapshot()

    assert [(item.metric, item.count) for item in snapshot.counts] == [
        (AnalysisCounter.CACHE_HIT, 3),
        (AnalysisCounter.CACHE_MISS, 1),
    ]
    assert [
        (item.metric, item.samples, item.total_seconds, item.max_seconds)
        for item in snapshot.durations
    ] == [(AnalysisDuration.REVISION_LOOKUP_SECONDS, 2, 0.4, 0.3)]


@pytest.mark.parametrize("count", [0, -1])
def test_rejects_non_positive_counter_increments(count: int) -> None:
    from codeatlas_analysis.analysis_telemetry import (
        AnalysisCounter,
        InMemoryAnalysisTelemetry,
    )

    with pytest.raises(ValueError, match="positive"):
        InMemoryAnalysisTelemetry().increment(AnalysisCounter.CACHE_HIT, count)


@pytest.mark.parametrize("duration", [-0.1, math.inf, math.nan])
def test_rejects_invalid_durations(duration: float) -> None:
    from codeatlas_analysis.analysis_telemetry import (
        AnalysisDuration,
        InMemoryAnalysisTelemetry,
    )

    with pytest.raises(ValueError, match="finite"):
        InMemoryAnalysisTelemetry().observe(AnalysisDuration.ARCHIVE_DOWNLOAD_SECONDS, duration)


def test_null_observer_accepts_valid_measurements_without_state() -> None:
    from codeatlas_analysis.analysis_telemetry import (
        AnalysisCounter,
        AnalysisDuration,
        NullAnalysisObserver,
    )

    observer = NullAnalysisObserver()
    observer.increment(AnalysisCounter.CACHE_SKIP)
    observer.observe(AnalysisDuration.ANALYSIS_SECONDS, 0.25)
