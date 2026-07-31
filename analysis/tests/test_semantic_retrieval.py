import pytest

from codeatlas_analysis.repository_acquisition import (
    RepositoryFile,
    RepositorySnapshot,
)
from codeatlas_analysis.repository_intake import normalize_public_github_repository
from codeatlas_analysis.repository_structure import (
    RepositoryStructure,
    analyze_repository,
)
from codeatlas_analysis.tree_sitter_parser import parse_source_module


def _structure() -> RepositoryStructure:
    sources = (
        (
            "src/auth/validate-session.ts",
            "export function validateSession() {}\n",
        ),
        (
            "src/accounts/account-repository.ts",
            "export class AccountRepository {}\n",
        ),
    )
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository("https://github.com/example/project"),
        revision="0123456789abcdef0123456789abcdef01234567",
        files=tuple(
            RepositoryFile(
                path=path,
                content=source,
                size_bytes=len(source.encode()),
            )
            for path, source in sources
        ),
    )
    return analyze_repository(snapshot, parse_source_module)


class ConceptEmbedder:
    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        vectors = []
        for text in texts:
            normalized = text.lower()
            if any(term in normalized for term in ("auth", "login", "session", "sign in")):
                vectors.append((1.0, 0.0))
            elif "account" in normalized:
                vectors.append((0.0, 1.0))
            else:
                vectors.append((0.0, 0.0))
        return tuple(vectors)


def test_semantic_retrieval_recovers_a_lexical_paraphrase() -> None:
    from codeatlas_analysis.retrieval import RetrievalMethod, RetrievalStatus, retrieve_evidence
    from codeatlas_analysis.semantic_retrieval import retrieve_semantic_evidence

    structure = _structure()
    query = "Where do users sign in?"

    assert retrieve_evidence(structure, query).status is RetrievalStatus.INSUFFICIENT_EVIDENCE

    result = retrieve_semantic_evidence(
        structure, query, embedder=ConceptEmbedder(), threshold=0.7, limit=1
    )

    assert result.status is RetrievalStatus.FOUND
    assert result.evidence[0].citation.path == "src/auth/validate-session.ts"
    assert result.evidence[0].citation.symbol == "validateSession"
    assert result.evidence[0].method is RetrievalMethod.SEMANTIC
    assert result.evidence[0].matched_terms == ()


def test_semantic_retrieval_preserves_insufficient_evidence_below_threshold() -> None:
    from codeatlas_analysis.retrieval import RetrievalStatus
    from codeatlas_analysis.semantic_retrieval import retrieve_semantic_evidence

    result = retrieve_semantic_evidence(
        _structure(),
        "billing invoices",
        embedder=ConceptEmbedder(),
        threshold=0.7,
    )

    assert result.status is RetrievalStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence == ()


def test_semantic_retrieval_rejects_an_invalid_embedding_batch() -> None:
    from codeatlas_analysis.semantic_retrieval import (
        EmbeddingContractError,
        retrieve_semantic_evidence,
    )

    class BrokenEmbedder:
        def embed(self, _texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
            return ((1.0,),)

    with pytest.raises(EmbeddingContractError, match="one vector per text"):
        retrieve_semantic_evidence(
            _structure(), "Where do users sign in?", embedder=BrokenEmbedder()
        )
