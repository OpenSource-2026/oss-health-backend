"""Hot-reload the vendored model in response to `model_promoted` webhooks.

Implements the backend side of oss-health-data's MODEL_UPDATE_CONTRACT.md.
The data pipeline owns drift detection, challenger training and promotion; the
backend's only job is to reload the five model artifacts when a new champion is
promoted, so subsequent diagnoses use the new model without a process restart.

Reload semantics (contract §5/§6):

- A new `model_version` triggers a reload; a repeat of the loaded version is a
  no-op. The version is tracked from the webhook payload — the bundled model
  metadata carries no timestamped version field.
- The five artifacts are loaded fully *before* any swap, so a failed/partial
  load never replaces a live model ("부분 교체하지 않는다"). On failure the
  currently loaded model is kept and the caller surfaces an error.
- The swap rebinds the module-level globals the vendored engine reads at call
  time (`inference.oss_health_diagnosis`), so in-flight and future diagnoses
  pick up the new model. A lock serialises concurrent reloads.

Where it reloads from: the producer's `backend_handoff_models_path` is honoured
only when that directory exists on this host (same-host deployments). In the
usual split deployment it does not, so we reload from the backend's own vendored
`pipeline/models/` — the artifacts a deploy/file-sync updates in place.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from pathlib import Path
from typing import Any

import joblib

from app.schemas.model_update import ModelPromotedEvent

logger = logging.getLogger(__name__)

# Repo layout mirrors diagnosis_service: <repo_root>/pipeline holds the vendored
# engine; put it on sys.path so `import inference.oss_health_diagnosis` resolves
# its internal absolute imports the same way the diagnosis path does.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PIPELINE_DIR = _REPO_ROOT / "pipeline"
_VENDORED_MODELS_DIR = _PIPELINE_DIR / "models"

if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

# Required base artifacts; meta artifacts are optional (the engine treats a
# missing meta model as "no meta correction"), matching engine._load_artifacts.
_REQUIRED_FILES = (
    "oss_health_best_model.joblib",
    "oss_health_best_features.json",
    "oss_health_model_metadata.json",
)

_lock = threading.Lock()
_loaded_model_version: str | None = None


class ModelReloadError(RuntimeError):
    """Raised when new artifacts cannot be loaded; the live model is kept."""


def current_model_version() -> str | None:
    """The model version currently loaded via a webhook, or None if never set."""
    return _loaded_model_version


def _load_artifacts(models_dir: Path) -> dict[str, Any]:
    """Load the five model artifacts from `models_dir`.

    Mirrors the vendored engine's loader (base model + features + metadata
    required, meta model + features optional). Raises ModelReloadError if a
    required file is missing or any file fails to load, so the caller can keep
    the live model instead of swapping in a half-loaded one.
    """
    missing = [name for name in _REQUIRED_FILES if not (models_dir / name).is_file()]
    if missing:
        raise ModelReloadError(f"missing artifacts in {models_dir}: {', '.join(missing)}")

    try:
        with open(models_dir / "oss_health_best_features.json", encoding="utf-8") as f:
            base_features = json.load(f)
        with open(models_dir / "oss_health_model_metadata.json", encoding="utf-8") as f:
            metadata = json.load(f)
        base_model = joblib.load(models_dir / "oss_health_best_model.joblib")

        meta_model = None
        meta_features: list[str] = []
        meta_model_path = models_dir / "oss_health_meta_model.joblib"
        meta_features_path = models_dir / "oss_health_meta_features.json"
        if meta_model_path.is_file() and meta_model_path.stat().st_size > 0:
            meta_model = joblib.load(meta_model_path)
        if meta_features_path.is_file() and meta_features_path.stat().st_size > 0:
            with open(meta_features_path, encoding="utf-8") as f:
                meta_features = json.load(f)
    except ModelReloadError:
        raise
    except Exception as exc:  # corrupt/incompatible artifact
        raise ModelReloadError(f"failed loading artifacts from {models_dir}: {exc}") from exc

    return {
        "MODEL": base_model,
        "MODEL_FEATURES": base_features,
        "MODEL_METADATA": metadata,
        "META_MODEL": meta_model,
        "META_FEATURES": meta_features,
    }


def _resolve_models_dir(payload_path: str | None) -> Path:
    """Pick where to reload from: the producer's path if present here, else vendored."""
    if payload_path:
        candidate = Path(payload_path)
        if candidate.is_dir() and all((candidate / name).is_file() for name in _REQUIRED_FILES):
            logger.info("Reloading model from producer-provided path %s", candidate)
            return candidate
        logger.info(
            "Producer path %r not usable on this host; reloading from vendored %s",
            payload_path,
            _VENDORED_MODELS_DIR,
        )
    return _VENDORED_MODELS_DIR


def _apply(artifacts: dict[str, Any]) -> None:
    """Atomically rebind the engine's module globals to the new artifacts.

    The vendored `diagnose_repository` reads `MODEL`, `MODEL_FEATURES`,
    `MODEL_METADATA`, `META_MODEL` and `META_FEATURES` from its module namespace
    at call time, so reassigning them here is picked up by the next diagnosis.
    """
    import inference.oss_health_diagnosis as engine

    engine.MODEL = artifacts["MODEL"]
    engine.MODEL_FEATURES = artifacts["MODEL_FEATURES"]
    engine.MODEL_METADATA = artifacts["MODEL_METADATA"]
    engine.META_MODEL = artifacts["META_MODEL"]
    engine.META_FEATURES = artifacts["META_FEATURES"]


def handle_model_promoted(event: ModelPromotedEvent) -> dict[str, Any]:
    """Handle a `model_promoted` event; reload the model when the version is new.

    Returns a result dict (reloaded / reason / model_version). Raises
    ModelReloadError when artifacts cannot be loaded — the live model is left
    untouched and the route maps this to an error response so the producer's
    alerting records the failure.
    """
    global _loaded_model_version

    if event.event_type != "model_promoted":
        logger.info("Ignoring non-promotion event_type=%r", event.event_type)
        return {
            "reloaded": False,
            "reason": "ignored_event_type",
            "model_version": _loaded_model_version,
        }

    with _lock:
        if event.model_version == _loaded_model_version:
            return {
                "reloaded": False,
                "reason": "same_model_version",
                "model_version": _loaded_model_version,
            }

        models_dir = _resolve_models_dir(event.backend_handoff_models_path)
        artifacts = _load_artifacts(models_dir)  # raises -> live model kept
        _apply(artifacts)
        _loaded_model_version = event.model_version
        logger.info("Reloaded model to version %s from %s", event.model_version, models_dir)
        return {
            "reloaded": True,
            "reason": "model_reloaded",
            "model_version": event.model_version,
        }
