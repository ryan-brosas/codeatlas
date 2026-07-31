from collections import defaultdict, deque
from dataclasses import dataclass
from enum import StrEnum

from codeatlas_analysis.repository_structure import (
    ParseStatus,
    RelationshipResolution,
    RepositoryStructure,
    SymbolRelationship,
)
from codeatlas_analysis.retrieval import (
    EvidenceRetriever,
    RetrievalMethod,
    RetrievalStatus,
    RetrievedEvidence,
    SourceCitation,
    retrieve_evidence,
)

_PROXIMITY_WARNING = "Dependency proximity identifies possible impact, not certainty."


class ImpactConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class ImpactedModule:
    path: str
    depth: int
    evidence: SourceCitation


@dataclass(frozen=True, slots=True)
class ChangeImpactReport:
    query: str
    status: RetrievalStatus
    candidates: tuple[RetrievedEvidence, ...]
    impacts: tuple[ImpactedModule, ...]
    location_confidence: ImpactConfidence
    warnings: tuple[str, ...]
    truncated: bool


def _location_confidence(
    candidate: RetrievedEvidence | None, *, incomplete_source: bool
) -> ImpactConfidence:
    if candidate is None:
        return ImpactConfidence.LOW
    if (
        candidate.method is RetrievalMethod.LEXICAL
        and len(candidate.matched_terms) >= 2
        and not incomplete_source
    ):
        return ImpactConfidence.HIGH
    return ImpactConfidence.MEDIUM


def _reverse_relationships(
    structure: RepositoryStructure,
) -> dict[str, tuple[SymbolRelationship, ...]]:
    by_target: dict[str, list[SymbolRelationship]] = defaultdict(list)
    for relationship in structure.relationships:
        if (
            relationship.resolution is RelationshipResolution.RESOLVED
            and relationship.target_module_path is not None
        ):
            by_target[relationship.target_module_path].append(relationship)
    return {
        path: tuple(
            sorted(
                relationships,
                key=lambda item: (
                    item.source_module_path,
                    item.span.start_line,
                    item.local_name,
                ),
            )
        )
        for path, relationships in by_target.items()
    }


def _traverse_impacts(
    structure: RepositoryStructure,
    root_path: str,
    *,
    max_depth: int,
    max_modules: int,
) -> tuple[tuple[ImpactedModule, ...], bool]:
    reverse = _reverse_relationships(structure)
    visited = {root_path}
    queue = deque([(root_path, 0)])
    impacts: list[ImpactedModule] = []
    truncated = False

    while queue:
        current_path, depth = queue.popleft()
        relationships = reverse.get(current_path, ())
        if depth >= max_depth:
            if any(item.source_module_path not in visited for item in relationships):
                truncated = True
            continue
        for relationship in relationships:
            next_path = relationship.source_module_path
            if next_path in visited:
                continue
            if len(impacts) >= max_modules:
                truncated = True
                continue
            visited.add(next_path)
            next_depth = depth + 1
            impacts.append(
                ImpactedModule(
                    path=next_path,
                    depth=next_depth,
                    evidence=SourceCitation(
                        path=next_path,
                        start_line=relationship.span.start_line,
                        end_line=relationship.span.end_line,
                        symbol=relationship.local_name,
                    ),
                )
            )
            queue.append((next_path, next_depth))
    return tuple(impacts), truncated


def analyze_change_impact(
    structure: RepositoryStructure,
    query: str,
    *,
    retriever: EvidenceRetriever = retrieve_evidence,
    max_depth: int = 3,
    max_modules: int = 100,
) -> ChangeImpactReport:
    if max_depth < 1 or max_modules < 1:
        raise ValueError("Impact traversal bounds must be positive.")

    retrieval = retriever(structure, query, limit=1)
    candidate = retrieval.evidence[0] if retrieval.evidence else None
    unresolved_count = sum(
        relationship.resolution
        not in (RelationshipResolution.RESOLVED, RelationshipResolution.EXTERNAL)
        for relationship in structure.relationships
    )
    partial_count = sum(module.status is ParseStatus.PARTIAL for module in structure.modules)
    incomplete_source = unresolved_count > 0 or partial_count > 0

    impacts: tuple[ImpactedModule, ...] = ()
    truncated = False
    if candidate is not None:
        impacts, truncated = _traverse_impacts(
            structure,
            candidate.citation.path,
            max_depth=max_depth,
            max_modules=max_modules,
        )

    warnings = [_PROXIMITY_WARNING]
    if candidate is None:
        warnings.append("No implementation candidate matched the available source evidence.")
    if unresolved_count:
        warnings.append(f"{unresolved_count} internal relationships could not be resolved.")
    if partial_count:
        warnings.append(f"{partial_count} modules contain partial parse evidence.")
    if truncated:
        warnings.append("Impact traversal stopped at the configured boundary.")

    return ChangeImpactReport(
        query=query,
        status=retrieval.status,
        candidates=retrieval.evidence,
        impacts=impacts,
        location_confidence=_location_confidence(candidate, incomplete_source=incomplete_source),
        warnings=tuple(warnings),
        truncated=truncated,
    )
