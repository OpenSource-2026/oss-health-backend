# OSS Health Checker — Backend image
#
# Single-stage build on python:3.12-slim. Application is run as a non-root
# user. The container exposes port 8000 and serves the FastAPI app via
# uvicorn. Container health is verified by hitting GET /api/v1/health.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python dependencies first so the layer is cached across rebuilds
# whenever only application code changes.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy application source.
COPY app ./app

# Drop privileges: create a non-root user and hand over /app ownership.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Readiness/liveness check used by docker-compose and orchestrators.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
