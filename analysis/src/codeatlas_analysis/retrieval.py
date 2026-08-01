import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from codeatlas_analysis.repository_structure import RepositoryStructure

_WORD = re.compile(r"[A-Za-z]+|[0-9]+")
_CAMEL_WORD = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|[0-9]+")
_SYMBOL_PRECISION_WEIGHT = 0.25
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "implemented",
    "in",
    "is",
    "of",
    "the",
    "to",
    "what",
    "where",
    "which",
}


class EvidenceBasis(StrEnum):
    VERIFIED_SOURCE = "verified_source"


class EvidenceKind(StrEnum):
    MODULE = "module"
    RELATIONSHIP = "relationship"
    SYMBOL = "symbol"


class RetrievalMethod(StrEnum):
    LEXICAL = "lexical"
    SEMANTIC = "semantic"


class RetrievalStatus(StrEnum):
    FOUND = "found"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class SourceCitation:
    path: str
    start_line: int
    end_line: int
    symbol: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievedEvidence:
    kind: EvidenceKind
    basis: EvidenceBasis
    citation: SourceCitation
    score: float
    matched_terms: tuple[str, ...]
    method: RetrievalMethod = RetrievalMethod.LEXICAL


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    query: str
    status: RetrievalStatus
    evidence: tuple[RetrievedEvidence, ...]


class EvidenceRetriever(Protocol):
    def __call__(
        self, structure: RepositoryStructure, query: str, *, limit: int
    ) -> RetrievalResult: ...


@dataclass(frozen=True, slots=True)
class EvidenceDocument:
    kind: EvidenceKind
    citation: SourceCitation
    text: str


def evidence_documents(structure: RepositoryStructure) -> tuple[EvidenceDocument, ...]:
    documents: list[EvidenceDocument] = []
    for module in structure.modules:
        documents.append(
            EvidenceDocument(
                kind=EvidenceKind.MODULE,
                citation=SourceCitation(path=module.path, start_line=1, end_line=1),
                text=module.path,
            )
        )
        for symbol in module.symbols:
            documents.append(
                EvidenceDocument(
                    kind=EvidenceKind.SYMBOL,
                    citation=SourceCitation(
                        path=module.path,
                        start_line=symbol.span.start_line,
                        end_line=symbol.span.end_line,
                        symbol=symbol.name,
                    ),
                    text=f"{module.path} {symbol.name} {symbol.kind.value}",
                )
            )
    for relationship in structure.relationships:
        documents.append(
            EvidenceDocument(
                kind=EvidenceKind.RELATIONSHIP,
                citation=SourceCitation(
                    path=relationship.source_module_path,
                    start_line=relationship.span.start_line,
                    end_line=relationship.span.end_line,
                    symbol=relationship.local_name,
                ),
                text=(
                    f"{relationship.source_module_path} {relationship.local_name} "
                    f"{relationship.specifier} "
                    f"{relationship.target_module_path or ''} "
                    f"{relationship.target_symbol_name}"
                ),
            )
        )
    return tuple(documents)


def _stem(term: str) -> str:
    if len(term) > 5 and term.endswith("ing"):
        return term[:-3]
    return term


def _terms(text: str) -> set[str]:
    terms: set[str] = set()
    for word in _WORD.findall(text):
        for part in _CAMEL_WORD.findall(word):
            normalized = _stem(part.lower())
            if normalized not in _STOP_WORDS:
                terms.add(normalized)
    return terms


def _symbol_precision(document: EvidenceDocument, query_terms: set[str]) -> float:
    if document.kind is not EvidenceKind.SYMBOL or document.citation.symbol is None:
        return 0.0
    symbol_terms = _terms(document.citation.symbol)
    if not symbol_terms:
        return 0.0
    return len(query_terms & symbol_terms) / len(symbol_terms)


def _lexical_evidence(
    document: EvidenceDocument, query_terms: set[str]
) -> RetrievedEvidence | None:
    matched_terms = tuple(sorted(query_terms & _terms(document.text)))
    if not matched_terms:
        return None
    return RetrievedEvidence(
        kind=document.kind,
        basis=EvidenceBasis.VERIFIED_SOURCE,
        citation=document.citation,
        score={
            EvidenceKind.MODULE: 0.0,
            EvidenceKind.RELATIONSHIP: 0.5,
            EvidenceKind.SYMBOL: 1.0,
        }[document.kind]
        + len(matched_terms) / len(query_terms)
        + _SYMBOL_PRECISION_WEIGHT * _symbol_precision(document, query_terms),
        matched_terms=matched_terms,
        method=RetrievalMethod.LEXICAL,
    )


def evidence_sort_key(item: RetrievedEvidence) -> tuple[float, int, str, int, str]:
    kind_order = {
        EvidenceKind.SYMBOL: 0,
        EvidenceKind.RELATIONSHIP: 1,
        EvidenceKind.MODULE: 2,
    }
    return (
        -item.score,
        kind_order[item.kind],
        item.citation.path,
        item.citation.start_line,
        item.citation.symbol or "",
    )


def retrieve_evidence(
    structure: RepositoryStructure, query: str, *, limit: int = 5
) -> RetrievalResult:
    query_terms = _terms(query)
    if not query_terms or limit <= 0:
        return RetrievalResult(
            query=query,
            status=RetrievalStatus.INSUFFICIENT_EVIDENCE,
            evidence=(),
        )

    candidates = tuple(
        evidence
        for document in evidence_documents(structure)
        if (evidence := _lexical_evidence(document, query_terms)) is not None
    )
    ranked = tuple(sorted(candidates, key=evidence_sort_key)[:limit])
    return RetrievalResult(
        query=query,
        status=(RetrievalStatus.FOUND if ranked else RetrievalStatus.INSUFFICIENT_EVIDENCE),
        evidence=ranked,
    )
