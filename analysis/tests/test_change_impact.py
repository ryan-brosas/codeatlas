from codeatlas_analysis.repository_acquisition import (
    RepositoryFile,
    RepositorySnapshot,
)
from codeatlas_analysis.repository_intake import normalize_public_github_repository
from codeatlas_analysis.repository_structure import (
    RepositoryStructure,
    analyze_repository,
)
from codeatlas_analysis.tree_sitter_parser import parse_source_module


def _structure() -> RepositoryStructure:
    sources = (
        (
            "src/core/session.ts",
            "export function validateSession() {}\n",
        ),
        (
            "src/features/login.ts",
            'import { validateSession } from "../core/session";\n'
            "export function login() { validateSession(); }\n",
        ),
        (
            "src/app.ts",
            'import { login } from "./features/login";\nexport function start() { login(); }\n',
        ),
    )
    snapshot = RepositorySnapshot(
        repository=normalize_public_github_repository("https://github.com/example/project"),
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
    return analyze_repository(snapshot, parse_source_module)


def test_locates_implementation_and_explains_direct_and_transitive_impact() -> None:
    from codeatlas_analysis.change_impact import (
        ImpactConfidence,
        analyze_change_impact,
    )
    from codeatlas_analysis.retrieval import RetrievalStatus

    report = analyze_change_impact(_structure(), "session validation function")

    assert report.status is RetrievalStatus.FOUND
    assert report.candidates[0].citation.symbol == "validateSession"
    assert report.location_confidence is ImpactConfidence.HIGH
    assert [
        (impact.path, impact.depth, impact.evidence.path, impact.evidence.start_line)
        for impact in report.impacts
    ] == [
        ("src/features/login.ts", 1, "src/features/login.ts", 1),
        ("src/app.ts", 2, "src/app.ts", 1),
    ]
    assert report.truncated is False
    assert report.warnings == ("Dependency proximity identifies possible impact, not certainty.",)


def test_reports_missing_location_evidence_without_guessing() -> None:
    from codeatlas_analysis.change_impact import (
        ImpactConfidence,
        analyze_change_impact,
    )
    from codeatlas_analysis.retrieval import RetrievalStatus

    report = analyze_change_impact(_structure(), "billing invoice workflow")

    assert report.status is RetrievalStatus.INSUFFICIENT_EVIDENCE
    assert report.candidates == ()
    assert report.impacts == ()
    assert report.location_confidence is ImpactConfidence.LOW
    assert "No implementation candidate matched the available source evidence." in report.warnings


def test_marks_a_bounded_impact_traversal_as_truncated() -> None:
    from codeatlas_analysis.change_impact import analyze_change_impact

    report = analyze_change_impact(_structure(), "session validation function", max_depth=1)

    assert [(impact.path, impact.depth) for impact in report.impacts] == [
        ("src/features/login.ts", 1)
    ]
    assert report.truncated is True
    assert "Impact traversal stopped at the configured boundary." in report.warnings
