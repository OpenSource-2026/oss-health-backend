"""Integration tests for POST /api/v1/analyze (mock response phase)."""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.response import HealthReport

client = TestClient(app)


def test_analyze_returns_200_for_valid_url() -> None:
    """A syntactically valid GitHub URL produces a 200 with the documented shape."""
    response = client.post(
        "/api/v1/analyze",
        json={"repo_url": "https://github.com/facebook/react"},
    )

    assert response.status_code == 200

    # Round-trip through the response model to assert the payload satisfies
    # the full schema, not just top-level keys.
    report = HealthReport.model_validate(response.json())
    assert report.repository.owner == "facebook"
    assert 0 <= report.health_score.total <= 100
    assert report.health_score.grade in {"A", "B", "C", "D", "F"}


def test_analyze_echoes_requested_url() -> None:
    """The mock echoes the request URL so the frontend can verify wiring."""
    repo_url = "https://github.com/python/cpython"
    response = client.post("/api/v1/analyze", json={"repo_url": repo_url})

    assert response.status_code == 200
    assert response.json()["repository"]["url"] == repo_url


def test_analyze_rejects_invalid_url() -> None:
    """Pydantic's HttpUrl validator rejects malformed URLs with 422."""
    response = client.post("/api/v1/analyze", json={"repo_url": "not-a-url"})

    assert response.status_code == 422


def test_analyze_response_contains_six_dimensions() -> None:
    """All six health dimensions from the analysis framework are present."""
    response = client.post(
        "/api/v1/analyze",
        json={"repo_url": "https://github.com/facebook/react"},
    )

    dimensions = response.json()["health_score"]["dimensions"]
    assert set(dimensions.keys()) == {
        "community_activity",
        "contributor_sustainability",
        "release_engineering",
        "governance",
        "maintenance",
        "adoption_popularity",
    }


def test_analyze_each_dimension_has_score_and_grade() -> None:
    """Every dimension exposes the score/grade/details contract the frontend renders."""
    response = client.post(
        "/api/v1/analyze",
        json={"repo_url": "https://github.com/facebook/react"},
    )

    dimensions = response.json()["health_score"]["dimensions"]
    for name, dim in dimensions.items():
        assert 0 <= dim["score"] <= 100, name
        assert dim["grade"] in {"A", "B", "C", "D", "F"}, name
        assert isinstance(dim["details"], dict) and dim["details"], name
