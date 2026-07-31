from codeatlas_analysis.repository_acquisition import (
    RepositoryFile,
    RepositorySnapshot,
)
from codeatlas_analysis.repository_intake import normalize_public_github_repository
from codeatlas_analysis.repository_structure import (
    ParseStatus,
    SourceLanguage,
    SourceModule,
    SymbolKind,
    analyze_repository,
)
from codeatlas_analysis.tree_sitter_parser import parse_source_module


class RecordingParser:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def __call__(self, file: RepositoryFile) -> SourceModule:
        self.paths.append(file.path)
        return SourceModule(
            path=file.path,
            language=SourceLanguage.TYPESCRIPT,
            status=ParseStatus.COMPLETE,
            symbols=(),
            dependencies=(),
        )


def test_builds_repository_file_and_module_structure() -> None:
    repository = normalize_public_github_repository("https://github.com/example/project")
    snapshot = RepositorySnapshot(
        repository=repository,
        revision="0123456789abcdef0123456789abcdef01234567",
        files=(
            RepositoryFile(
                path="package.json",
                content='{"name":"project"}',
                size_bytes=18,
            ),
            RepositoryFile(
                path="src/index.ts",
                content="export const value = 1;",
                size_bytes=23,
            ),
        ),
    )
    parser = RecordingParser()

    structure = analyze_repository(snapshot, parser)

    assert structure.repository == repository
    assert structure.revision == snapshot.revision
    assert [(file.path, file.language, file.size_bytes) for file in structure.files] == [
        ("package.json", SourceLanguage.JSON, 18),
        ("src/index.ts", SourceLanguage.TYPESCRIPT, 23),
    ]
    assert [module.path for module in structure.modules] == ["src/index.ts"]
    assert parser.paths == ["src/index.ts"]


def test_analyzes_a_snapshot_through_a_replaceable_parser_callable() -> None:
    source = "import { value } from './value';\nexport function run() {}\n"
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository("https://github.com/example/project"),
        revision="0123456789abcdef0123456789abcdef01234567",
        files=(
            RepositoryFile(
                path="src/index.ts",
                content=source,
                size_bytes=len(source.encode()),
            ),
        ),
    )

    structure = analyze_repository(snapshot, parse_source_module)

    assert structure == analyze_repository(snapshot, parse_source_module)
    assert [module.path for module in structure.modules] == ["src/index.ts"]
    assert [(symbol.name, symbol.kind) for symbol in structure.modules[0].symbols] == [
        ("run", SymbolKind.FUNCTION)
    ]
    assert [dependency.specifier for dependency in structure.modules[0].dependencies] == ["./value"]


def test_resolves_relative_modules_and_labels_unresolved_dependencies() -> None:
    index_source = (
        "import { User } from './user';\n"
        "import React from 'react';\n"
        "export { missing } from './missing';\n"
    )
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository("https://github.com/example/project"),
        revision="0123456789abcdef0123456789abcdef01234567",
        files=(
            RepositoryFile(
                path="src/index.ts",
                content=index_source,
                size_bytes=len(index_source.encode()),
            ),
            RepositoryFile(
                path="src/user.ts",
                content="export interface User {}\n",
                size_bytes=25,
            ),
        ),
    )

    structure = analyze_repository(snapshot, parse_source_module)

    dependencies = structure.modules[0].dependencies
    assert [
        (dependency.specifier, dependency.resolution.value, dependency.resolved_path)
        for dependency in dependencies
    ] == [
        ("./user", "resolved", "src/user.ts"),
        ("react", "external", None),
        ("./missing", "unresolved", None),
    ]


def test_does_not_guess_when_relative_module_resolution_is_ambiguous() -> None:
    source = "import { User } from './user';\n"
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository("https://github.com/example/project"),
        revision="0123456789abcdef0123456789abcdef01234567",
        files=(
            RepositoryFile(
                path="src/index.ts",
                content=source,
                size_bytes=len(source.encode()),
            ),
            RepositoryFile(path="src/user.js", content="", size_bytes=0),
            RepositoryFile(path="src/user.ts", content="", size_bytes=0),
        ),
    )

    dependency = analyze_repository(snapshot, parse_source_module).modules[0].dependencies[0]

    assert dependency.resolution.value == "ambiguous"
    assert dependency.resolved_path is None


def test_connects_imported_bindings_to_exported_source_symbols() -> None:
    index_source = (
        "import { User, Missing as LocalMissing } from './types';\n"
        "import { packageValue } from 'package';\n"
    )
    types_source = "export interface User {}\n"
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository("https://github.com/example/project"),
        revision="0123456789abcdef0123456789abcdef01234567",
        files=(
            RepositoryFile(
                path="src/index.ts",
                content=index_source,
                size_bytes=len(index_source.encode()),
            ),
            RepositoryFile(
                path="src/types.ts",
                content=types_source,
                size_bytes=len(types_source.encode()),
            ),
        ),
    )

    structure = analyze_repository(snapshot, parse_source_module)

    assert [
        (
            relationship.local_name,
            relationship.target_module_path,
            relationship.target_symbol_name,
            relationship.resolution.value,
        )
        for relationship in structure.relationships
    ] == [
        ("User", "src/types.ts", "User", "resolved"),
        ("LocalMissing", "src/types.ts", "Missing", "symbol_unresolved"),
        ("packageValue", None, "packageValue", "external"),
    ]


def test_resolves_default_imports_against_default_exports() -> None:
    index_source = "import UserService from './service';\n"
    service_source = "export default class UserService {}\n"
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository("https://github.com/example/project"),
        revision="0123456789abcdef0123456789abcdef01234567",
        files=(
            RepositoryFile(
                path="src/index.ts",
                content=index_source,
                size_bytes=len(index_source.encode()),
            ),
            RepositoryFile(
                path="src/service.ts",
                content=service_source,
                size_bytes=len(service_source.encode()),
            ),
        ),
    )

    relationship = analyze_repository(snapshot, parse_source_module).relationships[0]

    assert relationship.local_name == "UserService"
    assert relationship.target_symbol_name == "default"
    assert relationship.resolution.value == "resolved"


def test_represents_cyclic_import_and_re_export_relationships() -> None:
    first_source = "import { Second } from './second';\nexport interface First {}\n"
    second_source = "export interface Second {}\nexport { First as SharedFirst } from './first';\n"
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository("https://github.com/example/project"),
        revision="0123456789abcdef0123456789abcdef01234567",
        files=(
            RepositoryFile(
                path="src/first.ts",
                content=first_source,
                size_bytes=len(first_source.encode()),
            ),
            RepositoryFile(
                path="src/second.ts",
                content=second_source,
                size_bytes=len(second_source.encode()),
            ),
        ),
    )

    relationships = analyze_repository(snapshot, parse_source_module).relationships

    assert [
        (
            relationship.kind.value,
            relationship.source_module_path,
            relationship.local_name,
            relationship.target_module_path,
            relationship.target_symbol_name,
            relationship.resolution.value,
        )
        for relationship in relationships
    ] == [
        ("import", "src/first.ts", "Second", "src/second.ts", "Second", "resolved"),
        (
            "re_export",
            "src/second.ts",
            "SharedFirst",
            "src/first.ts",
            "First",
            "resolved",
        ),
    ]


def test_resolves_imports_through_named_re_export_chains() -> None:
    index_source = "import { PublicUser } from './barrel';\n"
    barrel_source = "export { User as PublicUser } from './types';\n"
    types_source = "export interface User {}\n"
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository("https://github.com/example/project"),
        revision="0123456789abcdef0123456789abcdef01234567",
        files=tuple(
            RepositoryFile(
                path=path,
                content=source,
                size_bytes=len(source.encode()),
            )
            for path, source in (
                ("src/barrel.ts", barrel_source),
                ("src/index.ts", index_source),
                ("src/types.ts", types_source),
            )
        ),
    )

    relationships = analyze_repository(snapshot, parse_source_module).relationships

    assert [relationship.resolution.value for relationship in relationships] == [
        "resolved",
        "resolved",
    ]
    assert relationships[1].target_symbol_name == "PublicUser"
