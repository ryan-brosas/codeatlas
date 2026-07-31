from fastapi.testclient import TestClient

from codeatlas_analysis.api import app


def test_health_reports_service_readiness() -> None:
    response = TestClient(app).get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "codeatlas-analysis",
        "status": "ok",
    }
