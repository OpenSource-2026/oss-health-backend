"""Integration tests for GET /api/v1/health."""

from fastapi.testclient import TestClient

from app import __version__
from app.main import app

client = TestClient(app)


def test_health_returns_200_and_version() -> None:
    """Health endpoint returns the documented payload shape."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    body = response.json()
    assert body == {"status": "ok", "version": __version__}


def test_health_response_schema_keys() -> None:
    """Response keys match the OpenAPI contract used by frontend and CI probes."""
    response = client.get("/api/v1/health")

    assert set(response.json().keys()) == {"status", "version"}
