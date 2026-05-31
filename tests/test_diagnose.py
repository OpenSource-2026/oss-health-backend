"""Integration tests for POST /api/oss-health/diagnose.

Hermetic by design: the data-pipeline engine call is monkeypatched so the
suite makes no GitHub network request and runs deterministically in CI.

- `live_engine` simulates a successful model run by returning the bundled
  sample payload through the same code path a real diagnosis takes
  (sanitize → `source: "live"`).
- `test_diagnose_sample_fallback_*` forces the engine to raise to exercise
  the fallback branch (`source: "sample"`).

The asserted contract is exactly what the frontend `ResultPage` renders.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.diagnosis import DiagnoseResponse

client = TestClient(app)

_FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "app" / "fixtures" / "sample_diagnosis.json").read_text(
        encoding="utf-8"
    )
)

EXPECTED_DIMENSIONS = {
    "community_activity",
    "sustainability",
    "code_quality_reliability",
    "legal_operational_governance",
    "project_maturity",
}


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset the diagnosis cache around every test for isolation.

    The cache persists in-process, so without this a `live` result cached by
    one test would be returned to the next (e.g. the sample-fallback test
    would get a cache hit and never exercise the fallback path).
    """
    import app.services.diagnosis_service as svc

    svc._cache.clear()
    yield
    svc._cache.clear()


@pytest.fixture
def live_engine(monkeypatch):
    """Patch the in-thread engine call to return a fresh copy of the fixture.

    Simulates a successful live diagnosis without touching the network or the
    real model, so the route's success path (sanitize + `source: live`) is
    tested deterministically.
    """
    import app.services.diagnosis_service as svc

    async def _fake_run_sync(_func, *_args, **_kwargs):
        return json.loads(json.dumps(_FIXTURE))  # deep copy

    monkeypatch.setattr(svc.anyio.to_thread, "run_sync", _fake_run_sync)


def _post(repo_url: str = "https://github.com/pallets/flask"):
    return client.post("/api/oss-health/diagnose", json={"repo_url": repo_url})


def test_diagnose_returns_200_with_contract_shape(live_engine) -> None:
    """A valid request returns 200 and a payload matching the data contract."""
    response = _post()
    assert response.status_code == 200

    report = DiagnoseResponse.model_validate(response.json())
    assert 0 <= report.overall_score <= 100
    assert report.overall_grade in {"Excellent", "Good", "Moderate", "Weak", "Risk"}
    assert len(report.dimension_scores) == 5
    assert response.json()["source"] == "live"


def test_diagnose_has_five_proposal_dimensions(live_engine) -> None:
    """All five proposal-aligned dimensions are present."""
    response = _post()
    dims = {d["dimension"] for d in response.json()["dimension_scores"]}
    assert dims == EXPECTED_DIMENSIONS


def test_diagnose_dimensions_expose_feature_insights(live_engine) -> None:
    """Each dimension exposes the strength/risk insight shape the UI renders."""
    response = _post()
    for dim in response.json()["dimension_scores"]:
        assert dim["grade"] in {"Excellent", "Good", "Moderate", "Weak", "Risk"}
        assert isinstance(dim["strength_features"], list)
        assert isinstance(dim["risk_features"], list)
        for feature in dim["strength_features"] + dim["risk_features"]:
            assert {"feature", "label", "score", "description"} <= feature.keys()


def test_diagnose_accepts_owner_repo_shorthand(live_engine) -> None:
    """The contract allows an `owner/repo` string, not only a full URL."""
    response = _post("pandas-dev/pandas")
    assert response.status_code == 200


def test_diagnose_rejects_missing_repo_url() -> None:
    """A request without repo_url fails validation with 422."""
    response = client.post("/api/oss-health/diagnose", json={})
    assert response.status_code == 422


def test_diagnose_caches_live_result(live_engine, monkeypatch) -> None:
    """A second request for the same repo is served from cache (no re-run)."""
    import app.services.diagnosis_service as svc

    calls = {"n": 0}
    real_uncached = svc.DiagnosisService._diagnose_uncached

    async def _counting(self, repo_url):
        calls["n"] += 1
        return await real_uncached(self, repo_url)

    monkeypatch.setattr(svc.DiagnosisService, "_diagnose_uncached", _counting)

    first = _post("pallets/flask")
    second = _post("pallets/flask")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert calls["n"] == 1  # engine ran once; second hit the cache


def test_diagnose_sample_fallback_marks_source(monkeypatch) -> None:
    """When live scoring fails, the sample fallback is served with source=sample."""
    import app.services.diagnosis_service as svc

    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated engine failure")

    # Force the in-thread engine call to fail so the fallback path is taken.
    monkeypatch.setattr(svc.anyio.to_thread, "run_sync", _boom)

    response = _post()
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "sample"
    assert body["repo_name"] == "pallets/flask"
    assert len(body["dimension_scores"]) == 5
