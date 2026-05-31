"""Repository diagnosis orchestration.

Bridges the API layer to the data-pipeline team's analysis engine
(vendored under `pipeline/`). The engine exposes a single entry point,
`diagnose_repository(repo_url)`, which fetches GitHub data, builds the
feature vector, runs the trained model, and returns the scored report in
the shape defined by `pipeline/API_CONTRACT.md`.

Two production concerns are handled here so the route handler stays thin:

1. **Blocking call off the event loop.** `diagnose_repository` does
   synchronous network I/O and scikit-learn inference, so it runs in a
   worker thread via `anyio.to_thread`.
2. **Graceful fallback.** If the engine import fails (deps missing), the
   GitHub call fails (no token / rate-limited / offline), or inference
   raises, we serve a bundled sample diagnosis so the frontend still has a
   complete, correctly-shaped response to render. The `source` field tells
   the client whether the result is `live` or `sample`.
"""

from __future__ import annotations

import json
import logging
import math
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import anyio

from app.metrics import CACHE_TOTAL, DIAGNOSE_TOTAL
from app.utils.cache import TTLCache

logger = logging.getLogger(__name__)

# Cache successful live diagnoses for an hour so repeated requests for the
# same repo skip the GitHub round-trip + model inference entirely.
_CACHE_TTL_SECONDS = 3600.0
_cache = TTLCache(_CACHE_TTL_SECONDS)

# Repo layout: <repo_root>/app/services/diagnosis_service.py and the vendored
# engine at <repo_root>/pipeline. Put the pipeline dir on sys.path so its
# internal absolute imports (`from inference...`, `from data...`) resolve.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PIPELINE_DIR = _REPO_ROOT / "pipeline"
_FIXTURE_PATH = _REPO_ROOT / "app" / "fixtures" / "sample_diagnosis.json"

if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))


def _sanitize(value: Any) -> Any:
    """Recursively replace NaN/Inf floats with None so the result is JSON-safe.

    A dimension with no measurable features can yield NaN scores; raw NaN/Inf
    are not valid JSON and would break serialization, so they become null.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


def _short_name(repo_url: str) -> str:
    """Best-effort `owner/repo` extraction for labelling the sample fallback."""
    match = re.search(r"github\.com[:/]([^/]+)/([^/#?]+)", repo_url)
    if match:
        return f"{match.group(1)}/{match.group(2).removesuffix('.git')}"
    if re.match(r"^[^/]+/[^/]+$", repo_url.strip()):
        return repo_url.strip()
    return repo_url


@lru_cache(maxsize=1)
def _load_sample() -> dict[str, Any]:
    """Load and cache the bundled sample diagnosis used for the fallback."""
    with open(_FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _sample_diagnosis(repo_url: str) -> dict[str, Any]:
    """Return the bundled sample, re-labelled with the requested repo."""
    sample = dict(_load_sample())
    sample["repo_name"] = _short_name(repo_url)
    sample["source"] = "sample"
    return sample


class DiagnosisService:
    """Run the health-diagnosis engine for a repository, with safe fallback."""

    async def diagnose(self, repo_url: str) -> dict[str, Any]:
        """Return a diagnosis dict for `repo_url`.

        Serves a cached result when available, otherwise a fresh `live`
        result from the model, falling back to the bundled `sample` fixture
        on any error. Always returns a complete, JSON-safe payload.
        """
        cache_key = _short_name(repo_url)
        cached = _cache.get(cache_key)
        if cached is not None:
            CACHE_TOTAL.labels(result="hit").inc()
            return cached
        CACHE_TOTAL.labels(result="miss").inc()

        result = await self._diagnose_uncached(repo_url)

        DIAGNOSE_TOTAL.labels(source=result.get("source", "live")).inc()
        # Only cache real model output — never a transient sample fallback,
        # so a temporary GitHub outage isn't pinned for an hour.
        if result.get("source") == "live":
            _cache.set(cache_key, result)
        return result

    async def _diagnose_uncached(self, repo_url: str) -> dict[str, Any]:
        """Run the engine (or fall back to the sample) without touching cache."""
        try:
            from inference.oss_health_diagnosis import diagnose_repository
        except Exception:  # pragma: no cover - exercised only when deps absent
            logger.warning(
                "Analysis engine unavailable (import failed); serving sample "
                "diagnosis. Install pipeline/requirements.txt for live scoring.",
                exc_info=True,
            )
            return _sample_diagnosis(repo_url)

        try:
            result = await anyio.to_thread.run_sync(diagnose_repository, repo_url)
        except Exception:
            logger.warning(
                "Live diagnosis failed for %r (no GITHUB_TOKEN, rate limit, or "
                "offline); serving sample diagnosis.",
                repo_url,
                exc_info=True,
            )
            return _sample_diagnosis(repo_url)

        result = _sanitize(result)
        result.setdefault("source", "live")
        return result
