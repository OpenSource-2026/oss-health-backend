"""FastAPI application entry point.

Run locally with:

    uvicorn app.main:app --reload --port 8000

OpenAPI docs are exposed at:
    - /docs    (Swagger UI)
    - /redoc   (ReDoc)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app import __version__
from app.api.router import api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="OSS Health Checker API",
    description=(
        "Backend service for the OSS Health Checker — analyses GitHub "
        "repositories across five health dimensions and returns scored "
        "reports with AI-generated improvement suggestions."
    ),
    version=__version__,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# Expose Prometheus metrics at GET /metrics (default HTTP metrics + the custom
# counters in app.metrics). Scraped by the Prometheus service in docker-compose
# and visualised in Grafana.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
