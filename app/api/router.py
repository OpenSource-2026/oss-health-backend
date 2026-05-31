"""Root API router that aggregates the public sub-routers.

Mounted by `app.main` under the `/api` prefix, producing:

    /api/oss-health/diagnose   canonical analysis endpoint (consumed by frontend)
    /api/v1/health             service health check

The analysis flow is model-backed via the vendored data pipeline; see
`app/api/oss_health.py`.
"""

from fastapi import APIRouter

from app.api import oss_health
from app.api.v1 import health

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health.router)

oss_health_router = APIRouter(prefix="/oss-health")
oss_health_router.include_router(oss_health.router)

api_router = APIRouter()
api_router.include_router(v1_router)
api_router.include_router(oss_health_router)
