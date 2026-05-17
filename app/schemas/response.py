"""Response schemas returned by the public API.

The shape mirrors the analysis-engine output contract agreed with the data
pipeline (김나경). Frontend (강수빈, 한예준) develops against this schema
via the mock response in `app/api/v1/analyze.py` while the real pipeline
and Gemini integrations are wired in during Phase G.
"""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

Grade = Literal["A", "B", "C", "D", "F"]


class Repository(BaseModel):
    """Basic GitHub repository metadata included in the analysis response."""

    name: str
    owner: str
    url: HttpUrl
    stars: int = Field(..., ge=0)
    forks: int = Field(..., ge=0)
    language: str | None = None


class DimensionScore(BaseModel):
    """Score for a single health dimension (e.g. community_activity)."""

    score: int = Field(..., ge=0, le=100)
    grade: Grade
    details: dict[str, int] = Field(
        ...,
        description=(
            "Per-sub-concept scores. Keys vary by dimension and are owned "
            "by the analysis pipeline (e.g. commit_frequency, pr_count for "
            "community_activity)."
        ),
    )


class HealthDimensions(BaseModel):
    """The six health dimensions evaluated for every repository.

    The dimension set matches the analysis engine's scoring framework:
    Community Activity, Contributor Sustainability, Release Engineering,
    Governance, Maintenance, Adoption / Popularity.
    """

    community_activity: DimensionScore
    contributor_sustainability: DimensionScore
    release_engineering: DimensionScore
    governance: DimensionScore
    maintenance: DimensionScore
    adoption_popularity: DimensionScore


class HealthScore(BaseModel):
    """Aggregate score across all five dimensions."""

    total: int = Field(..., ge=0, le=100)
    grade: Grade
    dimensions: HealthDimensions


class AIReport(BaseModel):
    """AI-generated narrative report. Produced by Gemini in the real pipeline."""

    summary: str
    strengths: list[str]
    improvements: list[str]


class HealthReport(BaseModel):
    """Top-level response payload for `POST /api/v1/analyze`."""

    repository: Repository
    health_score: HealthScore
    ai_report: AIReport
