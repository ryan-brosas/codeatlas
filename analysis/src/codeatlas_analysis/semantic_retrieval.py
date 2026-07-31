import math
from typing import Protocol

from codeatlas_analysis.repository_structure import RepositoryStructure
from codeatlas_analysis.retrieval import (
    EvidenceBasis,
    RetrievalMethod,
    RetrievalResult,
    RetrievalStatus,
    RetrievedEvidence,
    evidence_documents,
    evidence_sort_key,
)


class TextEmbedder(Protocol):
    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...


class EmbeddingContractError(ValueError):
    pass


def _validate_embeddings(vectors: tuple[tuple[float, ...], ...], expected_count: int) -> None:
    if len(vectors) != expected_count:
        raise EmbeddingContractError("The embedder must return one vector per text.")
    if not vectors or not vectors[0]:
        raise EmbeddingContractError("Embedding vectors must have a fixed positive dimension.")
    dimension = len(vectors[0])
    if any(len(vector) != dimension for vector in vectors):
        raise EmbeddingContractError("Embedding vectors must share one fixed dimension.")
    if any(not math.isfinite(value) for vector in vectors for value in vector):
        raise EmbeddingContractError("Embedding vectors must contain only finite values.")


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def retrieve_semantic_evidence(
    structure: RepositoryStructure,
    query: str,
    *,
    embedder: TextEmbedder,
    threshold: float = 0.7,
    limit: int = 5,
) -> RetrievalResult:
    if not query.strip() or limit <= 0:
        return RetrievalResult(
            query=query,
            status=RetrievalStatus.INSUFFICIENT_EVIDENCE,
            evidence=(),
        )
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Semantic threshold must be between zero and one.")

    documents = evidence_documents(structure)
    texts = (query, *(document.text for document in documents))
    vectors = embedder.embed(texts)
    _validate_embeddings(vectors, len(texts))
    query_vector, document_vectors = vectors[0], vectors[1:]

    candidates = []
    for document, vector in zip(documents, document_vectors, strict=True):
        similarity = _cosine(query_vector, vector)
        if similarity < threshold:
            continue
        candidates.append(
            RetrievedEvidence(
                kind=document.kind,
                basis=EvidenceBasis.VERIFIED_SOURCE,
                citation=document.citation,
                score=similarity,
                matched_terms=(),
                method=RetrievalMethod.SEMANTIC,
            )
        )

    ranked = tuple(sorted(candidates, key=evidence_sort_key)[:limit])
    return RetrievalResult(
        query=query,
        status=(RetrievalStatus.FOUND if ranked else RetrievalStatus.INSUFFICIENT_EVIDENCE),
        evidence=ranked,
    )
