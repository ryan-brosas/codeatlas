from bisect import bisect_right
from dataclasses import dataclass

import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from codeatlas_analysis.repository_acquisition import RepositoryFile
from codeatlas_analysis.repository_structure import (
    DependencyKind,
    ModuleDependency,
    ParseDiagnostic,
    ParseStatus,
    SourceLanguage,
    SourceModule,
    SourceSpan,
    SourceSymbol,
    SymbolBinding,
    SymbolKind,
    source_language_for_path,
)

_TYPESCRIPT = Language(tree_sitter_typescript.language_typescript())
_TSX = Language(tree_sitter_typescript.language_tsx())


class UnsupportedSourceLanguageError(ValueError):
    def __init__(self, path: str) -> None:
        super().__init__(f"Source file is not TypeScript or JavaScript: {path}")
        self.path = path


_SYMBOL_KIND_BY_NODE = {
    "class_declaration": SymbolKind.CLASS,
    "abstract_class_declaration": SymbolKind.CLASS,
    "enum_declaration": SymbolKind.ENUM,
    "function_declaration": SymbolKind.FUNCTION,
    "generator_function_declaration": SymbolKind.FUNCTION,
    "interface_declaration": SymbolKind.INTERFACE,
    "type_alias_declaration": SymbolKind.TYPE_ALIAS,
}


@dataclass(frozen=True, slots=True)
class _SourceCoordinates:
    content: bytes
    line_starts: tuple[int, ...]

    @classmethod
    def from_bytes(cls, content: bytes) -> "_SourceCoordinates":
        return cls(
            content=content,
            line_starts=(
                0,
                *(index + 1 for index, value in enumerate(content) if value == 10),
            ),
        )

    def text(self, node: Node) -> str:
        return self.content[node.start_byte : node.end_byte].decode()

    def position(self, byte_offset: int) -> tuple[int, int]:
        line_index = bisect_right(self.line_starts, byte_offset) - 1
        return line_index + 1, byte_offset - self.line_starts[line_index] + 1


def _span(node: Node, source: _SourceCoordinates) -> SourceSpan:
    start_line, start_column = source.position(node.start_byte)
    end_line, end_column = source.position(node.end_byte)
    return SourceSpan(
        start_line=start_line,
        start_column=start_column,
        end_line=end_line,
        end_column=end_column,
    )


def _node_text(source: _SourceCoordinates, node: Node) -> str:
    return source.text(node)


def _declaration_symbols(
    declaration: Node,
    source: _SourceCoordinates,
    *,
    exported: bool,
    default_export: bool = False,
) -> list[SourceSymbol]:
    kind = _SYMBOL_KIND_BY_NODE.get(declaration.type)
    if kind is not None:
        name = declaration.child_by_field_name("name")
        if name is None:
            return []
        name_text = _node_text(source, name)
        return [
            SourceSymbol(
                name=name_text,
                kind=kind,
                exported=exported,
                span=_span(declaration, source),
                export_name=("default" if default_export else name_text if exported else None),
            )
        ]
    if declaration.type not in {"lexical_declaration", "variable_declaration"}:
        return []
    symbols: list[SourceSymbol] = []
    for declarator in declaration.named_children:
        if declarator.type != "variable_declarator":
            continue
        name = declarator.child_by_field_name("name")
        if name is None or name.type != "identifier":
            continue
        symbols.append(
            SourceSymbol(
                name=_node_text(source, name),
                kind=SymbolKind.VARIABLE,
                exported=exported,
                span=_span(declarator, source),
                export_name=_node_text(source, name) if exported else None,
            )
        )
    return symbols


def _module_specifier(source: _SourceCoordinates, node: Node) -> str:
    literal = _node_text(source, node)
    return literal[1:-1]


def _named_binding(
    node: Node,
    source: _SourceCoordinates,
    *,
    specifier: str,
    kind: DependencyKind,
) -> SymbolBinding | None:
    name = node.child_by_field_name("name")
    if name is None:
        return None
    alias = node.child_by_field_name("alias")
    imported_name = _node_text(source, name)
    return SymbolBinding(
        specifier=specifier,
        imported_name=imported_name,
        local_name=_node_text(source, alias) if alias is not None else imported_name,
        kind=kind,
        span=_span(node, source),
    )


def _import_bindings(
    statement: Node, source: _SourceCoordinates, specifier: str
) -> list[SymbolBinding]:
    clause = next(
        (child for child in statement.named_children if child.type == "import_clause"),
        None,
    )
    if clause is None:
        return []
    bindings: list[SymbolBinding] = []
    for child in clause.named_children:
        if child.type == "identifier":
            bindings.append(
                SymbolBinding(
                    specifier=specifier,
                    imported_name="default",
                    local_name=_node_text(source, child),
                    kind=DependencyKind.IMPORT,
                    span=_span(child, source),
                )
            )
        elif child.type == "named_imports":
            for item in child.named_children:
                binding = _named_binding(
                    item, source, specifier=specifier, kind=DependencyKind.IMPORT
                )
                if binding is not None:
                    bindings.append(binding)
        elif child.type == "namespace_import":
            name = next(
                (item for item in child.named_children if item.type == "identifier"),
                None,
            )
            if name is not None:
                bindings.append(
                    SymbolBinding(
                        specifier=specifier,
                        imported_name="*",
                        local_name=_node_text(source, name),
                        kind=DependencyKind.IMPORT,
                        span=_span(child, source),
                    )
                )
    return bindings


def _re_export_bindings(
    statement: Node, source: _SourceCoordinates, specifier: str
) -> list[SymbolBinding]:
    clause = next(
        (child for child in statement.named_children if child.type == "export_clause"),
        None,
    )
    if clause is None:
        return (
            [
                SymbolBinding(
                    specifier=specifier,
                    imported_name="*",
                    local_name="*",
                    kind=DependencyKind.RE_EXPORT,
                    span=_span(statement, source),
                )
            ]
            if any(child.type == "*" for child in statement.children)
            else []
        )
    bindings: list[SymbolBinding] = []
    for item in clause.named_children:
        binding = _named_binding(item, source, specifier=specifier, kind=DependencyKind.RE_EXPORT)
        if binding is not None:
            bindings.append(binding)
    return bindings


def _syntax_diagnostics(root: Node, source: _SourceCoordinates) -> tuple[ParseDiagnostic, ...]:
    diagnostics: list[ParseDiagnostic] = []
    pending = list(reversed(root.children))
    while pending:
        node = pending.pop()
        if node.type == "ERROR":
            diagnostics.append(ParseDiagnostic(message="Syntax error.", span=_span(node, source)))
        elif node.is_missing:
            diagnostics.append(
                ParseDiagnostic(
                    message=f"Missing {node.type}.",
                    span=_span(node, source),
                )
            )
        pending.extend(reversed(node.children))
    return tuple(diagnostics)


def parse_source_module(file: RepositoryFile) -> SourceModule:
    language = source_language_for_path(file.path)
    if language is SourceLanguage.JSON:
        raise UnsupportedSourceLanguageError(file.path)
    source = _SourceCoordinates.from_bytes(file.content.encode())
    grammar = _TSX if language in {SourceLanguage.JSX, SourceLanguage.TSX} else _TYPESCRIPT
    root = Parser(grammar).parse(source.content).root_node
    symbols: list[SourceSymbol] = []
    dependencies: list[ModuleDependency] = []
    bindings: list[SymbolBinding] = []
    for node in root.named_children:
        if node.type == "import_statement":
            specifier = node.child_by_field_name("source")
            if specifier is not None:
                specifier_text = _module_specifier(source, specifier)
                dependencies.append(
                    ModuleDependency(
                        specifier=specifier_text,
                        kind=DependencyKind.IMPORT,
                        span=_span(node, source),
                    )
                )
                bindings.extend(_import_bindings(node, source, specifier_text))
            continue
        if node.type == "export_statement":
            specifier = node.child_by_field_name("source")
            if specifier is not None:
                specifier_text = _module_specifier(source, specifier)
                dependencies.append(
                    ModuleDependency(
                        specifier=specifier_text,
                        kind=DependencyKind.RE_EXPORT,
                        span=_span(node, source),
                    )
                )
                bindings.extend(_re_export_bindings(node, source, specifier_text))
            declaration = node.child_by_field_name("declaration")
            if declaration is not None:
                symbols.extend(
                    _declaration_symbols(
                        declaration,
                        source,
                        exported=True,
                        default_export=any(child.type == "default" for child in node.children),
                    )
                )
            continue
        symbols.extend(_declaration_symbols(node, source, exported=False))

    return SourceModule(
        path=file.path,
        language=language,
        status=ParseStatus.PARTIAL if root.has_error else ParseStatus.COMPLETE,
        symbols=tuple(symbols),
        dependencies=tuple(dependencies),
        bindings=tuple(bindings),
        diagnostics=_syntax_diagnostics(root, source),
    )
