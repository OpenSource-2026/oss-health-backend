"""Root API router that aggregates versioned sub-routers.

Each API version owns its own `APIRouter` and is mounted under a version
prefix here. New versions (e.g. v2) can be added without touching v1 code.
"""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/v1")
