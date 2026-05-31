"""Schemas for `POST /api/oss-health/diagnose`.

These mirror the contract the data-pipeline team published in
`pipeline/API_CONTRACT.md` and that the frontend (`ResultPage.jsx`) already
consumes: a model-based `overall_score`, five proposal-aligned dimension
scores, and per-feature strength/risk insights.

The backend is a thin orchestration layer over the pipeline's
`diagnose_repository()`; this schema is the shared boundary between the
analysis engine, the API, and the React dashboard.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PipelineGrade = Literal["Excellent", "Good", "Moderate", "Weak", "Risk"]


class DiagnoseRequest(BaseModel):
    """Payload for `POST /api/oss-health/diagnose`."""

    repo_url: str = Field(
        ...,
        description=(
            "GitHub repository URL or `owner/repo` string to analyse, e.g. "
            "https://github.com/pallets/flask or pallets/flask"
        ),
        examples=["https://github.com/pallets/flask", "pandas-dev/pandas"],
    )


class FeatureInsight(BaseModel):
    """A single strength or risk signal within a dimension.

    `feature` is the internal model feature key (kept for debugging);
    `label`/`description` are the Korean user-facing strings the dashboard
    renders.
    """

    feature: str
    label: str
    score: float
    description: str


class DimensionScore(BaseModel):
    """Percentile-based score for one of the five health dimensions."""

    dimension: str
    label: str
    # Optional: a dimension with no measurable features yields a NaN score,
    # sanitized to null. The frontend renders null as "-".
    score: float | None = None
    grade: PipelineGrade
    core_question: str
    concepts: str
    summary: str
    strength_features: list[FeatureInsight] = Field(default_factory=list)
    risk_features: list[FeatureInsight] = Field(default_factory=list)


class AIReport(BaseModel):
    """Optional Gemini-generated narrative report.

    Only present when a real `GEMINI_API_KEY` is configured. The frontend
    already derives a data-based "improvement TOP 3" from `risk_features`,
    so this is additive, not required.
    """

    summary: str
    strengths: list[str]
    improvements: list[str]


class DiagnoseResponse(BaseModel):
    """Top-level response for `POST /api/oss-health/diagnose`."""

    # `model_name` would otherwise collide with Pydantic's protected `model_`
    # namespace; the field name is part of the data team's contract.
    model_config = ConfigDict(protected_namespaces=())

    repo_name: str
    overall_score: float
    healthy_probability: float
    overall_grade: PipelineGrade
    model_name: str | None = None
    target: str | None = None
    dimension_scores: list[DimensionScore]
    ai_report: AIReport | None = None
    source: Literal["live", "sample"] = Field(
        default="live",
        description=(
            "`live` when scored by the model against freshly fetched GitHub "
            "data; `sample` when a bundled fixture was served (no token / "
            "GitHub unreachable) so the demo still works end-to-end."
        ),
    )
