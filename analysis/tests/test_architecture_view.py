from codeatlas_analysis.repository_acquisition import (
    RepositoryFile,
    RepositorySnapshot,
)
from codeatlas_analysis.repository_intake import normalize_public_github_repository
from codeatlas_analysis.repository_structure import analyze_repository
from codeatlas_analysis.tree_sitter_parser import parse_source_module


def test_builds_a_source_cited_architecture_view_with_explicit_limits() -> None:
    from codeatlas_analysis.architecture_view import build_architecture_view

    sources = (
        ("src/broken.ts", "export const = ;\nexport const valid = 1;\n"),
        (
            "src/index.ts",
            "import { User } from './types';\n"
            "import React from 'react';\n"
            "import { missing } from './missing';\n"
            "export function load() {}\n"
            "const privateValue = 1;\n",
        ),
        ("src/types.ts", "export interface User {}\n"),
    )
    repository = normalize_public_github_repository("https://github.com/example/project")
    snapshot = RepositorySnapshot(
        repository=repository,
        revision="0123456789abcdef0123456789abcdef01234567",
        files=tuple(
            RepositoryFile(
                path=path,
                content=source,
                size_bytes=len(source.encode()),
            )
            for path, source in sources
        ),
    )
    structure = analyze_repository(snapshot, parse_source_module)

    view = build_architecture_view(structure)

    assert view.repository == repository
    assert view.revision == snapshot.revision
    assert [module.path for module in view.modules] == [
        "src/broken.ts",
        "src/index.ts",
        "src/types.ts",
    ]
    assert [
        (module.path, [(symbol.name, symbol.kind.value, symbol.line) for symbol in module.symbols])
        for module in view.modules
    ] == [
        ("src/broken.ts", [("valid", "variable", 2)]),
        ("src/index.ts", [("load", "function", 4)]),
        ("src/types.ts", [("User", "interface", 1)]),
    ]
    assert [
        (
            relationship.source_path,
            relationship.line,
            relationship.local_name,
            relationship.target_path,
            relationship.target_symbol,
            relationship.resolution.value,
        )
        for relationship in view.relationships
    ] == [
        ("src/index.ts", 1, "User", "src/types.ts", "User", "resolved"),
        ("src/index.ts", 2, "React", None, "default", "external"),
        ("src/index.ts", 3, "missing", None, "missing", "module_unresolved"),
    ]
    assert [
        (limitation.code.value, limitation.path, limitation.line, limitation.subject)
        for limitation in view.limitations
    ] == [
        ("partial_parse", "src/broken.ts", 1, "Syntax error."),
        ("external_dependency", "src/index.ts", 2, "react"),
        ("unresolved_module", "src/index.ts", 3, "./missing"),
    ]
