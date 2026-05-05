"""Response schemas returned by the public API.

Mirrors the contract documented in README.md and docs/proposal.md so that
the frontend (강수빈, 한예준) can develop against this shape using mock
responses while the real analysis pipeline (김나경) is integrated.
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
            "Per-sub-concept scores. Keys vary by dimension "
            "(e.g. activity_volume, responsiveness for community_activity)."
        ),
    )


class HealthDimensions(BaseModel):
    """The five health dimensions evaluated for every repository."""

    community_activity: DimensionScore
    sustainability: DimensionScore
    code_quality: DimensionScore
    governance: DimensionScore
    maturity: DimensionScore


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
