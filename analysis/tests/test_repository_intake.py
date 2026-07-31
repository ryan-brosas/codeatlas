import pytest
from fastapi.testclient import TestClient

from codeatlas_analysis.api import app
from codeatlas_analysis.repository_intake import RepositoryStatus


def test_submit_public_github_repository_returns_pending_identity() -> None:
    response = TestClient(app).post(
        "/v1/repositories",
        json={"repository_url": "https://github.com/Vercel/Next.js.git/"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "repository": {
            "id": "github.com/vercel/next.js",
            "host": "github.com",
            "owner": "vercel",
            "name": "next.js",
            "canonical_url": "https://github.com/vercel/next.js",
        },
        "status": "pending",
    }


def test_rejects_unsupported_repository_host_with_typed_error() -> None:
    response = TestClient(app, raise_server_exceptions=False).post(
        "/v1/repositories",
        json={"repository_url": "https://gitlab.com/example/project"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "unsupported_repository_host",
            "message": "Only public GitHub repositories are supported.",
            "field": "repository_url",
        }
    }


@pytest.mark.parametrize(
    ("repository_url", "error_code"),
    [
        ("not-a-url", "invalid_repository_url"),
        ("http://github.com/owner/repository", "unsupported_repository_scheme"),
        ("https://gitlab.com/owner/repository", "unsupported_repository_host"),
        ("https://user@github.com/owner/repository", "unsafe_repository_url"),
        ("https://@github.com/owner/repository", "unsafe_repository_url"),
        ("https://:@github.com/owner/repository", "unsafe_repository_url"),
        ("https://github.com:443/owner/repository", "unsafe_repository_url"),
        ("https://github.com/owner/repository?tab=readme", "unsafe_repository_url"),
        ("https://github.com/owner/repository#readme", "unsafe_repository_url"),
        ("https://github.com/owner", "invalid_repository_path"),
        ("https://github.com/owner/repository/tree/main", "invalid_repository_path"),
        ("https://github.com//owner/repository", "invalid_repository_path"),
        ("https://github.com/owner/repo%2Fother", "invalid_repository_path"),
        ("https://github.com/owner/\nrepository", "invalid_repository_url"),
        ("https://github.com/owner/repository\t", "invalid_repository_url"),
    ],
)
def test_rejects_invalid_repository_urls_with_stable_codes(
    repository_url: str,
    error_code: str,
) -> None:
    response = TestClient(app, raise_server_exceptions=False).post(
        "/v1/repositories",
        json={"repository_url": repository_url},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == error_code


def test_openapi_documents_repository_request_success_and_errors() -> None:
    response = TestClient(app).get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/v1/repositories"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RepositoryIntakeRequest"
    }
    assert operation["responses"]["202"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RepositoryIntakeResponse"
    }
    for status_code in ("400", "422"):
        assert operation["responses"][status_code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ApiErrorResponse"
        }


def test_repository_analysis_states_are_explicit() -> None:
    assert {state.value for state in RepositoryStatus} == {
        "pending",
        "processing",
        "ready",
        "failed",
    }


def test_rejects_missing_repository_url_with_typed_error() -> None:
    response = TestClient(app).post("/v1/repositories", json={})

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": "Request validation failed.",
            "field": "repository_url",
        }
    }
