from fastapi.testclient import TestClient

from codeatlas_analysis.repository_acquisition import (
    AcquisitionErrorCode,
    RepositoryAcquisitionError,
    RepositoryFile,
    RepositorySnapshot,
)
from codeatlas_analysis.repository_analysis import RepositoryAnalysis
from codeatlas_analysis.repository_intake import RepositoryIdentity


class StaticSource:
    def __init__(self, source: str) -> None:
        self._source = source

    def acquire(self, repository: RepositoryIdentity) -> RepositorySnapshot:
        return RepositorySnapshot(
            repository=repository,
            revision="0123456789abcdef0123456789abcdef01234567",
            files=(
                RepositoryFile(
                    path="src/index.ts",
                    content=self._source,
                    size_bytes=len(self._source.encode()),
                ),
            ),
        )


def test_analyzes_a_public_repository_into_source_cited_architecture() -> None:
    from codeatlas_analysis.api import app, get_repository_analysis

    source = "export function run() {}\n"

    app.dependency_overrides[get_repository_analysis] = lambda: RepositoryAnalysis(
        StaticSource(source)
    )
    try:
        response = TestClient(app).post(
            "/v1/architecture",
            json={"repository_url": "https://github.com/Example/Project"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "repository": {
            "id": "github.com/example/project",
            "host": "github.com",
            "owner": "example",
            "name": "project",
            "canonical_url": "https://github.com/example/project",
        },
        "revision": "0123456789abcdef0123456789abcdef01234567",
        "modules": [
            {
                "path": "src/index.ts",
                "language": "typescript",
                "parse_status": "complete",
                "symbols": [{"name": "run", "kind": "function", "line": 1}],
            }
        ],
        "relationships": [],
        "limitations": [],
    }


def test_architecture_api_returns_typed_source_failures() -> None:
    from codeatlas_analysis.api import app, get_repository_analysis

    class UnavailableSource:
        def acquire(self, _repository: RepositoryIdentity) -> RepositorySnapshot:
            raise RepositoryAcquisitionError(
                AcquisitionErrorCode.SOURCE_UNAVAILABLE,
                "GitHub source is unavailable.",
            )

    app.dependency_overrides[get_repository_analysis] = lambda: RepositoryAnalysis(
        UnavailableSource()
    )
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/v1/architecture",
            json={"repository_url": "https://github.com/example/project"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "source_unavailable",
            "message": "GitHub source is unavailable.",
            "field": "repository_url",
        }
    }


def test_openapi_documents_architecture_success_and_source_errors() -> None:
    from codeatlas_analysis.api import app

    operation = TestClient(app).get("/openapi.json").json()["paths"]["/v1/architecture"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RepositoryIntakeRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ArchitectureView"
    }
    for status_code in ("400", "413", "422", "502"):
        assert operation["responses"][status_code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ApiErrorResponse"
        }


def test_answers_repository_questions_with_verified_citations() -> None:
    from codeatlas_analysis.api import app, get_repository_analysis

    source = "export function run() {}\n"

    app.dependency_overrides[get_repository_analysis] = lambda: RepositoryAnalysis(
        StaticSource(source)
    )
    try:
        response = TestClient(app).post(
            "/v1/questions",
            json={
                "repository_url": "https://github.com/example/project",
                "question": "Where is the run function?",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["inference"] == []
    assert body["facts"] == [
        {
            "text": "Source symbol run is declared at src/index.ts:1.",
            "basis": "verified_source",
            "citations": [
                {
                    "path": "src/index.ts",
                    "start_line": 1,
                    "end_line": 1,
                    "symbol": "run",
                }
            ],
        }
    ]
    assert body["evidence"][0]["basis"] == "verified_source"
    assert body["evidence"][0]["citation"]["symbol"] == "run"


def test_openapi_documents_cited_question_contract() -> None:
    from codeatlas_analysis.api import app

    operation = TestClient(app).get("/openapi.json").json()["paths"]["/v1/questions"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RepositoryQuestionRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CitedAnswer"
    }
    for status_code in ("400", "413", "422", "502"):
        assert operation["responses"][status_code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ApiErrorResponse"
        }


def test_reports_repository_change_impact_with_source_evidence() -> None:
    from codeatlas_analysis.api import app, get_repository_analysis

    sources = (
        ("src/core/session.ts", "export function validateSession() {}\n"),
        (
            "src/login.ts",
            'import { validateSession } from "./core/session";\n'
            "export function login() { validateSession(); }\n",
        ),
    )

    class ImpactSource:
        def acquire(self, repository: RepositoryIdentity) -> RepositorySnapshot:
            return RepositorySnapshot(
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

    app.dependency_overrides[get_repository_analysis] = lambda: RepositoryAnalysis(ImpactSource())
    try:
        response = TestClient(app).post(
            "/v1/impact",
            json={
                "repository_url": "https://github.com/example/project",
                "question": "session validation function",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "found"
    assert body["candidates"][0]["citation"]["symbol"] == "validateSession"
    assert body["location_confidence"] == "high"
    assert body["impacts"] == [
        {
            "path": "src/login.ts",
            "depth": 1,
            "evidence": {
                "path": "src/login.ts",
                "start_line": 1,
                "end_line": 1,
                "symbol": "validateSession",
            },
        }
    ]
    assert body["truncated"] is False


def test_openapi_documents_change_impact_contract() -> None:
    from codeatlas_analysis.api import app

    operation = TestClient(app).get("/openapi.json").json()["paths"]["/v1/impact"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RepositoryQuestionRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ChangeImpactReport"
    }
    for status_code in ("400", "413", "422", "502"):
        assert operation["responses"][status_code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ApiErrorResponse"
        }
