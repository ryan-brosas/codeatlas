from dataclasses import dataclass

from codeatlas_analysis.repository_acquisition import (
    RepositoryFile,
    RepositorySnapshot,
)
from codeatlas_analysis.repository_intake import (
    RepositoryIdentity,
    normalize_public_github_repository,
)


@dataclass(frozen=True)
class StaticSource:
    repository: RepositoryIdentity
    source: str
    path: str = "src/index.ts"

    def acquire(self, requested_repository: RepositoryIdentity) -> RepositorySnapshot:
        assert requested_repository == self.repository
        return RepositorySnapshot(
            repository=self.repository,
            revision="0123456789abcdef0123456789abcdef01234567",
            files=(
                RepositoryFile(
                    path=self.path,
                    content=self.source,
                    size_bytes=len(self.source.encode()),
                ),
            ),
        )


def test_runs_acquisition_parsing_and_architecture_projection() -> None:
    from codeatlas_analysis.repository_analysis import RepositoryAnalysis

    repository = normalize_public_github_repository("https://github.com/example/project")
    view = RepositoryAnalysis(StaticSource(repository, "export function run() {}\n")).analyze(
        repository
    )

    assert view.repository == repository
    assert view.revision == "0123456789abcdef0123456789abcdef01234567"
    assert [(module.path, module.symbols[0].name) for module in view.modules] == [
        ("src/index.ts", "run")
    ]


def test_runs_repository_questions_through_verified_source_retrieval() -> None:
    from codeatlas_analysis.cited_answers import AnswerStatus
    from codeatlas_analysis.repository_analysis import RepositoryAnalysis

    repository = normalize_public_github_repository("https://github.com/example/project")
    answer = RepositoryAnalysis(
        StaticSource(
            repository,
            "export function loadAccount() {}\n",
            "src/load-account.ts",
        )
    ).answer(repository, "account load function")

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.facts[0].citations[0].symbol == "loadAccount"


def test_keeps_semantic_provider_choice_outside_the_analysis_core() -> None:
    from codeatlas_analysis.repository_analysis import RepositoryAnalysis
    from codeatlas_analysis.repository_structure import RepositoryStructure
    from codeatlas_analysis.retrieval import RetrievalMethod, RetrievalResult
    from codeatlas_analysis.semantic_retrieval import retrieve_semantic_evidence

    class ConceptEmbedder:
        def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
            return tuple(
                (1.0,)
                if any(term in text.lower() for term in ("session", "sign in", "login"))
                else (0.0,)
                for text in texts
            )

    def semantic_retriever(
        structure: RepositoryStructure, query: str, *, limit: int
    ) -> RetrievalResult:
        return retrieve_semantic_evidence(structure, query, embedder=ConceptEmbedder(), limit=limit)

    repository = normalize_public_github_repository("https://github.com/example/project")
    analysis = RepositoryAnalysis(
        StaticSource(
            repository,
            "export function validateSession() {}\n",
            "src/auth/validate-session.ts",
        ),
        retriever=semantic_retriever,
    )

    answer = analysis.answer(repository, "Where do users sign in?")

    assert answer.evidence[0].citation.symbol == "validateSession"
    assert answer.evidence[0].method is RetrievalMethod.SEMANTIC
