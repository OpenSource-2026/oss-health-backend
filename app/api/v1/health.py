"""Liveness/health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response payload for the health check endpoint."""

    status: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Service health check")
async def health() -> HealthResponse:
    """Return service status and version.

    Used by orchestration tooling (Docker Compose health checks, CI smoke
    tests, monitoring probes) to verify the API process is up and serving
    requests.
    """
    return HealthResponse(status="ok", version=__version__)
