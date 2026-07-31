from codeatlas_analysis.repository_acquisition import (
    RepositoryFile,
    RepositorySnapshot,
)
from codeatlas_analysis.repository_intake import normalize_public_github_repository
from codeatlas_analysis.repository_structure import RepositoryStructure, analyze_repository
from codeatlas_analysis.tree_sitter_parser import parse_source_module


def _structure() -> RepositoryStructure:
    source = "export function loadAccount() {}\n"
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository("https://github.com/example/project"),
        revision="0123456789abcdef0123456789abcdef01234567",
        files=(
            RepositoryFile(
                path="src/accounts/load-account.ts",
                content=source,
                size_bytes=len(source.encode()),
            ),
        ),
    )
    return analyze_repository(snapshot, parse_source_module)


def test_answers_with_deterministic_verified_source_facts() -> None:
    from codeatlas_analysis.cited_answers import AnswerStatus, answer_question
    from codeatlas_analysis.retrieval import EvidenceBasis

    answer = answer_question(_structure(), "Where is the account load function?")

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.inference == ()
    assert answer.facts[0].basis is EvidenceBasis.VERIFIED_SOURCE
    assert answer.facts[0].text == (
        "Source symbol loadAccount is declared at src/accounts/load-account.ts:1."
    )
    assert answer.facts[0].citations == (answer.evidence[0].citation,)


def test_returns_insufficient_evidence_without_a_fact() -> None:
    from codeatlas_analysis.cited_answers import AnswerStatus, answer_question

    answer = answer_question(_structure(), "database migration schema")

    assert answer.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.facts == ()
    assert answer.evidence == ()
    assert answer.inference == ()


def test_rejects_blank_questions_as_unsupported() -> None:
    from codeatlas_analysis.cited_answers import AnswerStatus, answer_question

    answer = answer_question(_structure(), "  ")

    assert answer.status is AnswerStatus.UNSUPPORTED
    assert answer.facts == ()
    assert answer.evidence == ()
