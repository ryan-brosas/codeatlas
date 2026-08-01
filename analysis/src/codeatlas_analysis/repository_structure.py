from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import PurePosixPath
from posixpath import dirname, join, normpath
from typing import Protocol

from codeatlas_analysis.repository_acquisition import (
    RepositoryFile,
    RepositorySnapshot,
)
from codeatlas_analysis.repository_intake import RepositoryIdentity


class SourceLanguage(StrEnum):
    JAVASCRIPT = "javascript"
    JSON = "json"
    JSX = "jsx"
    TYPESCRIPT = "typescript"
    TSX = "tsx"


class SymbolKind(StrEnum):
    CLASS = "class"
    ENUM = "enum"
    FUNCTION = "function"
    INTERFACE = "interface"
    TYPE_ALIAS = "type_alias"
    VARIABLE = "variable"


class DependencyKind(StrEnum):
    IMPORT = "import"
    RE_EXPORT = "re_export"


class DependencyResolution(StrEnum):
    AMBIGUOUS = "ambiguous"
    EXTERNAL = "external"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class RelationshipResolution(StrEnum):
    AMBIGUOUS = "ambiguous"
    EXTERNAL = "external"
    MODULE_UNRESOLVED = "module_unresolved"
    RESOLVED = "resolved"
    SYMBOL_UNRESOLVED = "symbol_unresolved"


class ParseStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass(frozen=True, slots=True)
class SourceSymbol:
    name: str
    kind: SymbolKind
    exported: bool
    span: SourceSpan
    export_name: str | None = None


@dataclass(frozen=True, slots=True)
class ModuleDependency:
    specifier: str
    kind: DependencyKind
    span: SourceSpan
    resolution: DependencyResolution = DependencyResolution.UNRESOLVED
    resolved_path: str | None = None


@dataclass(frozen=True, slots=True)
class SymbolBinding:
    specifier: str
    imported_name: str
    local_name: str
    kind: DependencyKind
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ParseDiagnostic:
    message: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceModule:
    path: str
    language: SourceLanguage
    status: ParseStatus
    symbols: tuple[SourceSymbol, ...]
    dependencies: tuple[ModuleDependency, ...]
    bindings: tuple[SymbolBinding, ...] = ()
    diagnostics: tuple[ParseDiagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceFile:
    path: str
    language: SourceLanguage
    size_bytes: int


@dataclass(frozen=True, slots=True)
class SymbolRelationship:
    source_module_path: str
    specifier: str
    local_name: str
    target_module_path: str | None
    target_symbol_name: str
    kind: DependencyKind
    resolution: RelationshipResolution
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class RepositoryStructure:
    repository: RepositoryIdentity
    revision: str
    files: tuple[SourceFile, ...]
    modules: tuple[SourceModule, ...]
    relationships: tuple[SymbolRelationship, ...] = ()


class ModuleParser(Protocol):
    def __call__(self, file: RepositoryFile) -> SourceModule: ...


_CODE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
_DECLARATION_SUFFIXES = (".d.ts",)
_LANGUAGE_BY_SUFFIX = {
    ".cjs": SourceLanguage.JAVASCRIPT,
    ".js": SourceLanguage.JAVASCRIPT,
    ".json": SourceLanguage.JSON,
    ".jsx": SourceLanguage.JSX,
    ".mjs": SourceLanguage.JAVASCRIPT,
    ".ts": SourceLanguage.TYPESCRIPT,
    ".tsx": SourceLanguage.TSX,
}


def source_language_for_path(path: str) -> SourceLanguage:
    return _LANGUAGE_BY_SUFFIX[PurePosixPath(path).suffix.lower()]


def _resolve_dependency(
    module_path: str,
    dependency: ModuleDependency,
    source_paths: set[str],
) -> ModuleDependency:
    if not dependency.specifier.startswith("."):
        return replace(dependency, resolution=DependencyResolution.EXTERNAL)
    base = normpath(join(dirname(module_path), dependency.specifier))
    candidates: tuple[str, ...]
    if PurePosixPath(base).suffix in _CODE_SUFFIXES:
        candidates = (base,)
        matches = tuple(candidate for candidate in candidates if candidate in source_paths)
    else:
        candidates = tuple(base + suffix for suffix in _CODE_SUFFIXES) + tuple(
            join(base, "index" + suffix) for suffix in _CODE_SUFFIXES
        )
        matches = tuple(candidate for candidate in candidates if candidate in source_paths)
        if not matches:
            declarations = tuple(base + suffix for suffix in _DECLARATION_SUFFIXES) + tuple(
                join(base, "index" + suffix) for suffix in _DECLARATION_SUFFIXES
            )
            matches = tuple(candidate for candidate in declarations if candidate in source_paths)
    if len(matches) == 1:
        return replace(
            dependency,
            resolution=DependencyResolution.RESOLVED,
            resolved_path=matches[0],
        )
    if len(matches) > 1:
        return replace(dependency, resolution=DependencyResolution.AMBIGUOUS)
    return dependency


def _binding_dependency(module: SourceModule, binding: SymbolBinding) -> ModuleDependency | None:
    return next(
        (
            item
            for item in module.dependencies
            if item.specifier == binding.specifier and item.kind is binding.kind
        ),
        None,
    )


def _exported_names(modules: tuple[SourceModule, ...]) -> dict[str, set[str]]:
    exported = {
        module.path: {
            symbol.export_name for symbol in module.symbols if symbol.export_name is not None
        }
        for module in modules
    }
    changed = True
    while changed:
        changed = False
        for module in modules:
            for binding in module.bindings:
                if binding.kind is not DependencyKind.RE_EXPORT:
                    continue
                dependency = _binding_dependency(module, binding)
                if (
                    dependency is None
                    or dependency.resolution is not DependencyResolution.RESOLVED
                    or dependency.resolved_path is None
                ):
                    continue
                target_exports = exported.get(dependency.resolved_path, set())
                if binding.imported_name == "*":
                    new_names = target_exports - {"default"} - exported[module.path]
                    if new_names:
                        exported[module.path].update(new_names)
                        changed = True
                    continue
                if (
                    binding.imported_name not in target_exports
                    or binding.local_name in exported[module.path]
                ):
                    continue
                exported[module.path].add(binding.local_name)
                changed = True
    return exported


def _relationship_for_binding(
    module: SourceModule,
    binding: SymbolBinding,
    exported_names: dict[str, set[str]],
) -> SymbolRelationship | None:
    dependency = _binding_dependency(module, binding)
    if dependency is None:
        return None
    resolution_by_dependency = {
        DependencyResolution.AMBIGUOUS: RelationshipResolution.AMBIGUOUS,
        DependencyResolution.EXTERNAL: RelationshipResolution.EXTERNAL,
        DependencyResolution.UNRESOLVED: RelationshipResolution.MODULE_UNRESOLVED,
    }
    resolution = resolution_by_dependency.get(dependency.resolution)
    if resolution is None:
        target_exports = exported_names.get(dependency.resolved_path or "", set())
        resolution = (
            RelationshipResolution.RESOLVED
            if binding.imported_name == "*" or binding.imported_name in target_exports
            else RelationshipResolution.SYMBOL_UNRESOLVED
        )
    return SymbolRelationship(
        source_module_path=module.path,
        specifier=binding.specifier,
        local_name=binding.local_name,
        target_module_path=dependency.resolved_path,
        target_symbol_name=binding.imported_name,
        kind=binding.kind,
        resolution=resolution,
        span=binding.span,
    )


def analyze_repository(snapshot: RepositorySnapshot, parser: ModuleParser) -> RepositoryStructure:
    files = tuple(
        SourceFile(
            path=file.path,
            language=source_language_for_path(file.path),
            size_bytes=file.size_bytes,
        )
        for file in snapshot.files
    )
    parsed_modules = tuple(
        parser(file)
        for file, source_file in zip(snapshot.files, files, strict=True)
        if source_file.language is not SourceLanguage.JSON
    )
    source_paths = {file.path for file in files}
    modules = tuple(
        replace(
            module,
            dependencies=tuple(
                _resolve_dependency(module.path, dependency, source_paths)
                for dependency in module.dependencies
            ),
        )
        for module in parsed_modules
    )
    exported_names = _exported_names(modules)
    relationships = tuple(
        relationship
        for module in modules
        for binding in module.bindings
        if (relationship := _relationship_for_binding(module, binding, exported_names)) is not None
    )
    return RepositoryStructure(
        repository=snapshot.repository,
        revision=snapshot.revision,
        files=files,
        modules=modules,
        relationships=relationships,
    )
