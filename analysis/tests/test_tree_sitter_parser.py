import pytest

from codeatlas_analysis.repository_acquisition import RepositoryFile
from codeatlas_analysis.repository_structure import (
    DependencyKind,
    ParseStatus,
    SourceLanguage,
    SymbolKind,
)
from codeatlas_analysis.tree_sitter_parser import (
    UnsupportedSourceLanguageError,
    parse_source_module,
)


def test_extracts_typescript_symbols_and_module_dependencies() -> None:
    source = """import { User } from \"./user\";
export { audit } from \"./audit\";
export interface Account { id: string }
export class AccountService {}
export async function loadAccount(): Promise<Account> { throw new Error(); }
const localLimit = 10;
export const defaultLimit = 20;
"""

    module = parse_source_module(
        RepositoryFile(
            path="src/account.ts",
            content=source,
            size_bytes=len(source.encode()),
        )
    )

    assert module.path == "src/account.ts"
    assert module.language is SourceLanguage.TYPESCRIPT
    assert module.status is ParseStatus.COMPLETE
    assert [
        (symbol.name, symbol.kind, symbol.exported, symbol.span.start_line)
        for symbol in module.symbols
    ] == [
        ("Account", SymbolKind.INTERFACE, True, 3),
        ("AccountService", SymbolKind.CLASS, True, 4),
        ("loadAccount", SymbolKind.FUNCTION, True, 5),
        ("localLimit", SymbolKind.VARIABLE, False, 6),
        ("defaultLimit", SymbolKind.VARIABLE, True, 7),
    ]
    assert [
        (dependency.specifier, dependency.kind, dependency.span.start_line)
        for dependency in module.dependencies
    ] == [
        ("./user", DependencyKind.IMPORT, 1),
        ("./audit", DependencyKind.RE_EXPORT, 2),
    ]


def test_preserves_partial_evidence_with_syntax_diagnostics() -> None:
    source = "export const = ;\nexport const valid = 1;\n"

    module = parse_source_module(
        RepositoryFile(
            path="src/broken.ts",
            content=source,
            size_bytes=len(source.encode()),
        )
    )

    assert module.status is ParseStatus.PARTIAL
    assert [symbol.name for symbol in module.symbols] == ["valid"]
    assert module.diagnostics
    assert module.diagnostics[0].span.start_line == 1


def test_rejects_non_code_files_at_the_parser_boundary() -> None:
    with pytest.raises(UnsupportedSourceLanguageError) as raised:
        parse_source_module(
            RepositoryFile(
                path="package.json",
                content='{"name":"project"}',
                size_bytes=18,
            )
        )

    assert raised.value.path == "package.json"


@pytest.mark.parametrize(
    ("path", "source", "language"),
    [
        ("src/module.js", "export function run() {}", SourceLanguage.JAVASCRIPT),
        (
            "src/view.tsx",
            "export function View() { return <main />; }",
            SourceLanguage.TSX,
        ),
    ],
)
def test_parses_supported_javascript_and_tsx_modules(
    path: str, source: str, language: SourceLanguage
) -> None:
    module = parse_source_module(
        RepositoryFile(
            path=path,
            content=source,
            size_bytes=len(source.encode()),
        )
    )

    assert module.language is language
    assert module.status is ParseStatus.COMPLETE
    assert [symbol.name for symbol in module.symbols] == ["run" if path.endswith(".js") else "View"]


def test_extracts_imported_and_re_exported_symbol_bindings() -> None:
    source = """import DefaultThing, { User, Role as UserRole } from \"./types\";
import * as utils from \"./utils\";
export { User as PublicUser } from \"./types\";
export * from \"./more\";
"""

    module = parse_source_module(
        RepositoryFile(
            path="src/index.ts",
            content=source,
            size_bytes=len(source.encode()),
        )
    )

    assert [
        (
            binding.specifier,
            binding.imported_name,
            binding.local_name,
            binding.kind.value,
            binding.span.start_line,
        )
        for binding in module.bindings
    ] == [
        ("./types", "default", "DefaultThing", "import", 1),
        ("./types", "User", "User", "import", 1),
        ("./types", "Role", "UserRole", "import", 1),
        ("./utils", "*", "utils", "import", 2),
        ("./types", "User", "PublicUser", "re_export", 3),
        ("./more", "*", "*", "re_export", 4),
    ]


def test_large_declaration_spans_do_not_cross_native_point_lifetimes() -> None:
    import subprocess
    import sys

    source = (
        "export default function first() {\n"
        + "call();\n" * 500
        + "}\nexport function second() {}\n"
    )
    program = """
import sys
from codeatlas_analysis.repository_acquisition import RepositoryFile
from codeatlas_analysis.tree_sitter_parser import parse_source_module
source = sys.stdin.read()
module = parse_source_module(
    RepositoryFile(
        path="index.js",
        content=source,
        size_bytes=len(source.encode()),
    )
)
print([(symbol.name, symbol.span.end_line) for symbol in module.symbols])
"""

    completed = subprocess.run(
        [sys.executable, "-c", program],
        input=source,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "[('first', 502), ('second', 503)]"
