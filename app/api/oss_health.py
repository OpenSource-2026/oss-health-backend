"""POST /api/oss-health/diagnose — repository health diagnosis endpoint.

This is the canonical analysis endpoint consumed by the frontend
(`src/api/ossHealthApi.js`). It orchestrates:

    DiagnosisService  →  (optional) AIReportService

`DiagnosisService` runs the data-pipeline team's trained model over freshly
fetched GitHub data and always returns a complete, JSON-safe payload (live
or sample fallback). `AIReportService` optionally enriches it with a Gemini
narrative when a key is configured.

The request/response contract matches `pipeline/API_CONTRACT.md`.
"""

from fastapi import APIRouter

from app.schemas.diagnosis import DiagnoseRequest, DiagnoseResponse
from app.services.ai_report_service import AIReportService
from app.services.diagnosis_service import DiagnosisService

router = APIRouter(tags=["oss-health"])


@router.post(
    "/diagnose",
    response_model=DiagnoseResponse,
    response_model_exclude_none=True,
    summary="Diagnose a GitHub repository's open-source health",
)
async def diagnose(request: DiagnoseRequest) -> DiagnoseResponse:
    """Return a health diagnosis for the requested repository.

    Never fails on a recoverable analysis error: when live scoring is not
    possible (missing token, GitHub unreachable, deps absent) a bundled
    sample is returned with `source: "sample"` so the dashboard always has a
    complete result to render. The optional `ai_report` is included only
    when a real Gemini key is configured and the call succeeds.
    """
    diagnosis = await DiagnosisService().diagnose(request.repo_url)

    # Copy before attaching ai_report: the diagnosis dict may be a cached
    # object shared across requests, so it must not be mutated in place.
    payload = dict(diagnosis)
    ai_report = await AIReportService().generate(diagnosis)
    if ai_report is not None:
        payload["ai_report"] = ai_report.model_dump()

    return DiagnoseResponse.model_validate(payload)
