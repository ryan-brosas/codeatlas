from collections.abc import Callable
from time import monotonic
from typing import Protocol

from codeatlas_analysis.analysis_telemetry import (
    AnalysisDuration,
    AnalysisObserver,
    NullAnalysisObserver,
)
from codeatlas_analysis.architecture_view import (
    ArchitectureView,
    build_architecture_view,
)
from codeatlas_analysis.change_impact import (
    ChangeImpactReport,
    analyze_change_impact,
)
from codeatlas_analysis.cited_answers import CitedAnswer, answer_question
from codeatlas_analysis.repository_acquisition import RepositorySnapshot
from codeatlas_analysis.repository_intake import RepositoryIdentity
from codeatlas_analysis.repository_structure import (
    ModuleParser,
    RepositoryStructure,
    analyze_repository,
)
from codeatlas_analysis.retrieval import EvidenceRetriever, retrieve_evidence
from codeatlas_analysis.tree_sitter_parser import parse_source_module


class RepositorySource(Protocol):
    def acquire(self, repository: RepositoryIdentity) -> RepositorySnapshot: ...


class RepositoryAnalysis:
    def __init__(
        self,
        source: RepositorySource,
        parser: ModuleParser = parse_source_module,
        retriever: EvidenceRetriever = retrieve_evidence,
        observer: AnalysisObserver | None = None,
        now: Callable[[], float] = monotonic,
    ) -> None:
        self._source = source
        self._parser = parser
        self._retriever = retriever
        self._observer = observer or NullAnalysisObserver()
        self._now = now

    def _structure(self, repository: RepositoryIdentity) -> RepositoryStructure:
        started_at = self._now()
        try:
            snapshot = self._source.acquire(repository)
            return analyze_repository(snapshot, self._parser)
        finally:
            self._observer.observe(AnalysisDuration.ANALYSIS_SECONDS, self._now() - started_at)

    def analyze(self, repository: RepositoryIdentity) -> ArchitectureView:
        return build_architecture_view(self._structure(repository))

    def answer(self, repository: RepositoryIdentity, question: str) -> CitedAnswer:
        return answer_question(self._structure(repository), question, retriever=self._retriever)

    def impact(self, repository: RepositoryIdentity, question: str) -> ChangeImpactReport:
        return analyze_change_impact(
            self._structure(repository), question, retriever=self._retriever
        )
