"""Request schemas for the public API."""

from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    """Payload for `POST /api/v1/analyze`."""

    repo_url: HttpUrl = Field(
        ...,
        description=(
            "Full GitHub repository URL to analyse, e.g. "
            "https://github.com/facebook/react"
        ),
        examples=["https://github.com/facebook/react"],
    )
