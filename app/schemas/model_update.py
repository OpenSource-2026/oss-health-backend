"""Schemas for the data pipeline's `model_promoted` webhook.

Mirrors the payload defined in oss-health-data's
`src/backend_handoff/MODEL_UPDATE_CONTRACT.md` §4. The data pipeline POSTs
this event after it promotes a new champion model; the backend reloads the
model artifacts in response (see `app.services.model_reload_service`).
"""

from pydantic import BaseModel, Field


class ModelPromotedEvent(BaseModel):
    """A `model_promoted` event emitted by the data pipeline.

    Only `event_type` and `model_version` are required — the rest is context
    the producer sends and we log but do not strictly depend on. `extra` is
    ignored so the contract can grow new fields without breaking us.
    """

    # `model_version` is fixed by the contract; opt out of pydantic's "model_"
    # protected-namespace check so it doesn't warn about the field name.
    model_config = {"extra": "ignore", "protected_namespaces": ()}

    event_type: str = Field(description='Always "model_promoted".')
    model_version: str = Field(
        description="The newly promoted model version (e.g. UTC YYYYMMDD_HHMMSS)."
    )
    project: str | None = Field(default=None, description="Project identifier.")
    trigger_reason: str | None = Field(
        default=None,
        description='Why the model updated: "reference_changed" or "feature_drift".',
    )
    champion_path: str | None = Field(
        default=None, description="Producer-side champion registry path (informational)."
    )
    metadata_path: str | None = Field(
        default=None, description="Producer-side promotion metadata path (informational)."
    )
    backend_handoff_models_path: str | None = Field(
        default=None,
        description=(
            "Directory the producer wrote the new artifacts to. Used only when "
            "it exists on this host (same-host setups); otherwise the backend "
            "reloads from its own vendored pipeline/models directory."
        ),
    )
    created_at: str | None = Field(default=None, description="Event creation time.")
    producer: str | None = Field(default=None, description='Always "data-pipeline".')
    consumer: str | None = Field(default=None, description='Always "backend".')


class ModelReloadResult(BaseModel):
    """The outcome of handling a `model_promoted` event."""

    model_config = {"protected_namespaces": ()}

    reloaded: bool = Field(description="True when the in-memory model was swapped.")
    reason: str = Field(
        description=(
            "Machine-readable outcome: model_reloaded | same_model_version | "
            "ignored_event_type."
        )
    )
    model_version: str | None = Field(
        default=None, description="The model version currently loaded after handling."
    )
