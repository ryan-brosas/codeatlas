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
            "src/accounts/load-account.ts",
            "export function loadAccount() {}\nexport class AccountRepository {}\n",
        ),
        ("src/users/user.ts", "export interface User {}\n"),
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


def test_retrieves_ranked_verified_symbol_evidence() -> None:
    from codeatlas_analysis.retrieval import (
        EvidenceBasis,
        EvidenceKind,
        RetrievalStatus,
        retrieve_evidence,
    )

    result = retrieve_evidence(
        _structure(),
        "Where is the account load function implemented?",
        limit=3,
    )

    assert result.status is RetrievalStatus.FOUND
    assert len(result.evidence) <= 3
    assert result.evidence[0].kind is EvidenceKind.SYMBOL
    assert result.evidence[0].basis is EvidenceBasis.VERIFIED_SOURCE
    assert result.evidence[0].citation.path == "src/accounts/load-account.ts"
    assert result.evidence[0].citation.symbol == "loadAccount"
    assert result.evidence[0].citation.start_line == 1
    assert result.evidence[0].matched_terms == ("account", "function", "load")


def test_returns_insufficient_evidence_without_guessing() -> None:
    from codeatlas_analysis.retrieval import RetrievalStatus, retrieve_evidence

    result = retrieve_evidence(_structure(), "database migration schema")

    assert result.status is RetrievalStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence == ()


@pytest.mark.parametrize(
    ("query", "expected_path", "expected_symbol"),
    [
        ("account load function", "src/accounts/load-account.ts", "loadAccount"),
        (
            "account repository class",
            "src/accounts/load-account.ts",
            "AccountRepository",
        ),
        ("user interface", "src/users/user.ts", "User"),
    ],
)
def test_retrieval_fixture_ranks_expected_source_evidence_first(
    query: str, expected_path: str, expected_symbol: str
) -> None:
    from codeatlas_analysis.retrieval import retrieve_evidence

    top = retrieve_evidence(_structure(), query, limit=1).evidence[0]

    assert (top.citation.path, top.citation.symbol) == (
        expected_path,
        expected_symbol,
    )
