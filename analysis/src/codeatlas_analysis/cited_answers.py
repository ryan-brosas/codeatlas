from dataclasses import dataclass
from enum import StrEnum

from codeatlas_analysis.repository_structure import RepositoryStructure
from codeatlas_analysis.retrieval import (
    EvidenceBasis,
    EvidenceKind,
    EvidenceRetriever,
    RetrievalStatus,
    RetrievedEvidence,
    SourceCitation,
    retrieve_evidence,
)


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class CitedFact:
    text: str
    basis: EvidenceBasis
    citations: tuple[SourceCitation, ...]


@dataclass(frozen=True, slots=True)
class CitedAnswer:
    query: str
    status: AnswerStatus
    facts: tuple[CitedFact, ...]
    evidence: tuple[RetrievedEvidence, ...]
    inference: tuple[str, ...] = ()


def _fact_text(evidence: RetrievedEvidence) -> str:
    citation = evidence.citation
    location = f"{citation.path}:{citation.start_line}"
    if evidence.kind is EvidenceKind.SYMBOL and citation.symbol is not None:
        return f"Source symbol {citation.symbol} is declared at {location}."
    if evidence.kind is EvidenceKind.RELATIONSHIP and citation.symbol is not None:
        return f"Source relationship {citation.symbol} is declared at {location}."
    return f"Source module {citation.path} matches at {location}."


def answer_question(
    structure: RepositoryStructure,
    query: str,
    *,
    limit: int = 3,
    retriever: EvidenceRetriever = retrieve_evidence,
) -> CitedAnswer:
    if not query.strip():
        return CitedAnswer(
            query=query,
            status=AnswerStatus.UNSUPPORTED,
            facts=(),
            evidence=(),
        )
    retrieval = retriever(structure, query, limit=limit)
    if retrieval.status is RetrievalStatus.INSUFFICIENT_EVIDENCE:
        return CitedAnswer(
            query=query,
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            facts=(),
            evidence=(),
        )
    facts = tuple(
        CitedFact(
            text=_fact_text(evidence),
            basis=EvidenceBasis.VERIFIED_SOURCE,
            citations=(evidence.citation,),
        )
        for evidence in retrieval.evidence
    )
    return CitedAnswer(
        query=query,
        status=AnswerStatus.ANSWERED,
        facts=facts,
        evidence=retrieval.evidence,
    )
