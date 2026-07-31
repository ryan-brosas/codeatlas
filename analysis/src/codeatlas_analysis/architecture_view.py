from dataclasses import dataclass
from enum import StrEnum

from codeatlas_analysis.repository_intake import RepositoryIdentity
from codeatlas_analysis.repository_structure import (
    DependencyKind,
    ParseStatus,
    RelationshipResolution,
    RepositoryStructure,
    SourceLanguage,
    SymbolKind,
)


class LimitationCode(StrEnum):
    AMBIGUOUS_MODULE = "ambiguous_module"
    EXTERNAL_DEPENDENCY = "external_dependency"
    PARTIAL_PARSE = "partial_parse"
    UNRESOLVED_MODULE = "unresolved_module"
    UNRESOLVED_SYMBOL = "unresolved_symbol"


@dataclass(frozen=True, slots=True)
class ArchitectureSymbol:
    name: str
    kind: SymbolKind
    line: int


@dataclass(frozen=True, slots=True)
class ArchitectureModule:
    path: str
    language: SourceLanguage
    parse_status: ParseStatus
    symbols: tuple[ArchitectureSymbol, ...]


@dataclass(frozen=True, slots=True)
class ArchitectureRelationship:
    source_path: str
    line: int
    specifier: str
    local_name: str
    target_path: str | None
    target_symbol: str
    kind: DependencyKind
    resolution: RelationshipResolution


@dataclass(frozen=True, slots=True)
class ArchitectureLimitation:
    code: LimitationCode
    path: str
    line: int
    subject: str


@dataclass(frozen=True, slots=True)
class ArchitectureView:
    repository: RepositoryIdentity
    revision: str
    modules: tuple[ArchitectureModule, ...]
    relationships: tuple[ArchitectureRelationship, ...]
    limitations: tuple[ArchitectureLimitation, ...]


_LIMITATION_BY_RESOLUTION = {
    RelationshipResolution.AMBIGUOUS: LimitationCode.AMBIGUOUS_MODULE,
    RelationshipResolution.EXTERNAL: LimitationCode.EXTERNAL_DEPENDENCY,
    RelationshipResolution.MODULE_UNRESOLVED: LimitationCode.UNRESOLVED_MODULE,
    RelationshipResolution.SYMBOL_UNRESOLVED: LimitationCode.UNRESOLVED_SYMBOL,
}


def build_architecture_view(structure: RepositoryStructure) -> ArchitectureView:
    modules = tuple(
        ArchitectureModule(
            path=module.path,
            language=module.language,
            parse_status=module.status,
            symbols=tuple(
                ArchitectureSymbol(
                    name=symbol.name,
                    kind=symbol.kind,
                    line=symbol.span.start_line,
                )
                for symbol in module.symbols
                if symbol.export_name is not None
            ),
        )
        for module in structure.modules
    )
    relationships = tuple(
        ArchitectureRelationship(
            source_path=relationship.source_module_path,
            line=relationship.span.start_line,
            specifier=relationship.specifier,
            local_name=relationship.local_name,
            target_path=relationship.target_module_path,
            target_symbol=relationship.target_symbol_name,
            kind=relationship.kind,
            resolution=relationship.resolution,
        )
        for relationship in structure.relationships
    )
    parse_limitations = tuple(
        ArchitectureLimitation(
            code=LimitationCode.PARTIAL_PARSE,
            path=module.path,
            line=diagnostic.span.start_line,
            subject=diagnostic.message,
        )
        for module in structure.modules
        for diagnostic in module.diagnostics
    )
    relationship_limitations = tuple(
        ArchitectureLimitation(
            code=code,
            path=relationship.source_path,
            line=relationship.line,
            subject=relationship.specifier,
        )
        for relationship in relationships
        if (code := _LIMITATION_BY_RESOLUTION.get(relationship.resolution)) is not None
    )
    return ArchitectureView(
        repository=structure.repository,
        revision=structure.revision,
        modules=modules,
        relationships=relationships,
        limitations=parse_limitations + relationship_limitations,
    )
