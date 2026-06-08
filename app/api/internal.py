"""`/internal` — endpoints for the data pipeline, not the public frontend.

`POST /internal/model-promoted` is the backend side of oss-health-data's
MODEL_UPDATE_CONTRACT.md: the data pipeline calls it after promoting a new
champion model, and the backend hot-reloads the model artifacts so subsequent
diagnoses use the new model without a restart. Mounted at the app root (not
under `/api`) to match the contract path and the pipeline's
`oss_health_backend_webhook_url` variable.

This is an internal, same-network endpoint (called by Airflow, not browsers);
it is intentionally not behind CORS or auth. Put it behind network policy or a
shared secret before exposing the backend publicly.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.model_update import ModelPromotedEvent, ModelReloadResult
from app.services.model_reload_service import ModelReloadError, handle_model_promoted

logger = logging.getLogger(__name__)

router = APIRouter(tags=["internal"])


@router.post(
    "/model-promoted",
    response_model=ModelReloadResult,
    summary="Reload the model after the data pipeline promotes a new champion",
)
def model_promoted(event: ModelPromotedEvent) -> ModelReloadResult:
    """Reload model artifacts for a `model_promoted` event.

    Sync handler so FastAPI runs the blocking joblib load in its threadpool,
    keeping the event loop free. Returns 200 with `reloaded` true/false for
    handled events (new version vs. same version / ignored type); returns 500
    when the new artifacts fail to load — the live model is kept, and the 500
    lets the pipeline's alerting record the failed promotion.
    """
    try:
        result = handle_model_promoted(event)
    except ModelReloadError as exc:
        logger.error("Model reload failed for version %s: %s", event.model_version, exc)
        raise HTTPException(status_code=500, detail=f"model reload failed: {exc}") from exc
    return ModelReloadResult(**result)
