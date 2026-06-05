"""`/api/oss-health` — repository health diagnosis + result sharing.

`POST /diagnose` is the canonical analysis endpoint consumed by the frontend
(`src/api/ossHealthApi.js`). It orchestrates:

    DiagnosisService  →  (optional) AIReportService

`DiagnosisService` runs the data-pipeline team's trained model over freshly
fetched GitHub data and always returns a complete, JSON-safe payload (live
or sample fallback). `AIReportService` optionally enriches it with a Gemini
narrative when a key is configured.

`GET /result/{share_id}` returns a previously-computed diagnosis as-is, with
no re-analysis and no AI call. It backs the QR "view on phone" feature: the
dashboard renders a QR encoding the share link, and a phone that scans it
fetches the stored result here.

The request/response contract matches `pipeline/API_CONTRACT.md`.
"""

import hashlib

from fastapi import APIRouter, HTTPException

from app.schemas.diagnosis import DiagnoseRequest, DiagnoseResponse
from app.services.ai_report_service import AIReportService
from app.services.diagnosis_service import DiagnosisService
from app.utils.cache import TTLCache

router = APIRouter(tags=["oss-health"])

# Stores rendered diagnosis payloads by share id so the QR link can re-fetch
# the exact same result (incl. any AI report) without re-running the model or
# Gemini. In-process and TTL-bounded, matching the diagnosis cache; a phone
# scans the QR within seconds of analysis, well inside the window.
_RESULT_TTL_SECONDS = 3600.0
_results = TTLCache(_RESULT_TTL_SECONDS)


def _share_id(repo_name: str) -> str:
    """Deterministic short id for a repo, so re-analysing reuses one link."""
    return hashlib.sha256(repo_name.encode("utf-8")).hexdigest()[:10]


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

    # Register a share id and stash the payload so the QR link can re-fetch it.
    share_id = _share_id(payload.get("repo_name", request.repo_url))
    payload["share_id"] = share_id
    _results.set(share_id, payload)

    return DiagnoseResponse.model_validate(payload)


@router.get(
    "/result/{share_id}",
    response_model=DiagnoseResponse,
    response_model_exclude_none=True,
    summary="Fetch a previously-computed diagnosis by its share id",
)
async def get_result(share_id: str) -> DiagnoseResponse:
    """Return a stored diagnosis for the QR share link.

    404 if the id is unknown or expired (e.g. the backend restarted), so the
    phone can show a "re-run the analysis" message instead of a blank page.
    """
    payload = _results.get(share_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="결과를 찾을 수 없습니다. 분석을 다시 실행해주세요.",
        )
    return DiagnoseResponse.model_validate(payload)
