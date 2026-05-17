"""POST /api/v1/analyze — repository health analysis endpoint.

Orchestrates the three services that make up the analysis flow:

    GitHubService  →  AnalysisService  →  AIReportService

Each service still returns a mock today (Phase E), but the route handler
already talks to them through the real interfaces, so wiring in the
genuine pipeline (Phase G) is a service-internal change rather than a
route change.
"""

from fastapi import APIRouter, HTTPException, status

from app.schemas.request import AnalyzeRequest
from app.schemas.response import HealthReport, Repository
from app.services.ai_report_service import AIReportService
from app.services.analysis_service import AnalysisService
from app.services.github_service import InvalidGitHubURLError, RepoMetadata

router = APIRouter(tags=["analyze"])


def _repo_metadata_for(request: AnalyzeRequest) -> RepoMetadata:
    """Mock-stage RepoMetadata that echoes the requested URL.

    Used while `GitHubService.fetch_repo_metadata` is not yet wired into
    the flow (no live GitHub call during tests). Phase G replaces this
    with `await github.fetch_repo_metadata(...)`.
    """
    return RepoMetadata(
        name="react",
        owner="facebook",
        url=str(request.repo_url),
        stars=48221,
        forks=19774,
        language="JavaScript",
    )


@router.post(
    "/analyze",
    response_model=HealthReport,
    summary="Analyse a GitHub repository's open-source health",
)
async def analyze(request: AnalyzeRequest) -> HealthReport:
    """Return a `HealthReport` for the requested repository.

    Today every service returns a mock, so the response is deterministic.
    The route shape, error handling, and service-call order are the real
    contract the frontend, analysis pipeline, and Gemini integration all
    plug into during Phase G.
    """
    try:
        repo = _repo_metadata_for(request)
    except InvalidGitHubURLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    analysis = AnalysisService()
    ai_report = AIReportService()

    health_score = await analysis.score(repo)
    report = await ai_report.generate(health_score)

    return HealthReport(
        repository=Repository(
            name=repo.name,
            owner=repo.owner,
            url=repo.url,
            stars=repo.stars,
            forks=repo.forks,
            language=repo.language,
        ),
        health_score=health_score,
        ai_report=report,
    )
