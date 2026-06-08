"""Tests for POST /internal/model-promoted (data-pipeline model hot-reload).

Hermetic by default: the artifact loader and engine swap are monkeypatched so
the suite never reads joblib files or mutates the vendored engine. One opt-in
test exercises the real reload against the bundled artifacts to confirm the
engine global names the swap rebinds are correct; it is skipped if the pipeline
inference deps aren't installed.
"""

import pytest
from fastapi.testclient import TestClient

import app.services.model_reload_service as reload_svc
from app.main import app

client = TestClient(app)


def _event(**overrides):
    payload = {
        "event_type": "model_promoted",
        "project": "oss-health",
        "model_version": "20260608_031522",
        "trigger_reason": "feature_drift",
        "producer": "data-pipeline",
        "consumer": "backend",
    }
    payload.update(overrides)
    return payload


@pytest.fixture(autouse=True)
def _reset_loaded_version():
    """Reset the tracked model version around every test for isolation."""
    reload_svc._loaded_model_version = None
    yield
    reload_svc._loaded_model_version = None


@pytest.fixture
def fake_reload(monkeypatch):
    """Stub artifact loading + engine swap; record swaps without touching disk."""
    applied = []
    monkeypatch.setattr(reload_svc, "_load_artifacts", lambda models_dir: {"models_dir": models_dir})
    monkeypatch.setattr(reload_svc, "_apply", lambda artifacts: applied.append(artifacts))
    return applied


def test_new_version_triggers_reload(fake_reload):
    """A new model_version reloads the model and reports the version."""
    response = client.post("/internal/model-promoted", json=_event())
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "reloaded": True,
        "reason": "model_reloaded",
        "model_version": "20260608_031522",
    }
    assert len(fake_reload) == 1
    assert reload_svc.current_model_version() == "20260608_031522"


def test_same_version_is_noop(fake_reload):
    """Re-posting the loaded version does not reload again."""
    first = client.post("/internal/model-promoted", json=_event())
    assert first.json()["reloaded"] is True

    second = client.post("/internal/model-promoted", json=_event())
    assert second.status_code == 200
    assert second.json() == {
        "reloaded": False,
        "reason": "same_model_version",
        "model_version": "20260608_031522",
    }
    assert len(fake_reload) == 1  # only the first reloaded


def test_non_promotion_event_is_ignored(fake_reload):
    """A non-promotion event_type is acknowledged but never reloads."""
    response = client.post("/internal/model-promoted", json=_event(event_type="model_drift"))
    assert response.status_code == 200
    assert response.json()["reloaded"] is False
    assert response.json()["reason"] == "ignored_event_type"
    assert fake_reload == []


def test_reload_failure_returns_500_and_keeps_model(monkeypatch):
    """A failed artifact load returns 500 and leaves the loaded version intact."""

    def _boom(models_dir):
        raise reload_svc.ModelReloadError("corrupt artifact")

    monkeypatch.setattr(reload_svc, "_load_artifacts", _boom)
    monkeypatch.setattr(reload_svc, "_apply", lambda artifacts: pytest.fail("must not swap"))

    response = client.post("/internal/model-promoted", json=_event())
    assert response.status_code == 500
    assert "model reload failed" in response.json()["detail"]
    assert reload_svc.current_model_version() is None  # unchanged


def test_missing_model_version_is_422(fake_reload):
    """model_version is required by the contract; omitting it fails validation."""
    response = client.post("/internal/model-promoted", json=_event(model_version=None))
    assert response.status_code == 422


def test_real_reload_swaps_engine_globals(monkeypatch):
    """End-to-end: reloading from the vendored artifacts repopulates the engine.

    Guards against silent breakage if an engine global is renamed. Skipped when
    the pipeline inference deps (scikit-learn etc.) aren't installed.
    """
    engine = pytest.importorskip("inference.oss_health_diagnosis")

    snapshot = {
        name: getattr(engine, name)
        for name in ("MODEL", "MODEL_FEATURES", "MODEL_METADATA", "META_MODEL", "META_FEATURES")
    }
    try:
        response = client.post("/internal/model-promoted", json=_event(model_version="real-test-1"))
        assert response.status_code == 200
        assert response.json()["reloaded"] is True
        # Engine globals are repopulated (the swap found and rebound them).
        assert engine.MODEL is not None
        assert isinstance(engine.MODEL_FEATURES, list) and engine.MODEL_FEATURES
        assert isinstance(engine.MODEL_METADATA, dict) and engine.MODEL_METADATA
    finally:
        for name, value in snapshot.items():
            setattr(engine, name, value)
