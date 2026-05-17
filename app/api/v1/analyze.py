"""POST /api/v1/analyze — repository health analysis endpoint.

This module currently returns a hard-coded mock `HealthReport` so the
frontend team can develop against the real response shape while the data
pipeline (김나경) and Gemini integration (Phase E/G) are still under
construction. The mock will be replaced by a call to `analysis_service`
once the analysis engine interface is finalised.
"""

from fastapi import APIRouter

from app.schemas.request import AnalyzeRequest
from app.schemas.response import (
    AIReport,
    DimensionScore,
    HealthDimensions,
    HealthReport,
    HealthScore,
    Repository,
)

router = APIRouter(tags=["analyze"])


def _build_mock_report(request: AnalyzeRequest) -> HealthReport:
    """Construct a deterministic mock report aligned with the six-dimension schema.

    Echoes the requested URL inside `Repository.url` so the frontend can
    verify round-trip wiring during integration without depending on the
    real GitHub fetch. Per-dimension `details` keys are placeholder names
    pending the analysis pipeline's final sub-feature list.
    """
    return HealthReport(
        repository=Repository(
            name="react",
            owner="facebook",
            url=request.repo_url,
            stars=48221,
            forks=19774,
            language="JavaScript",
        ),
        health_score=HealthScore(
            total=82,
            grade="A",
            dimensions=HealthDimensions(
                community_activity=DimensionScore(
                    score=91,
                    grade="A",
                    details={
                        "commit_frequency": 95,
                        "pr_throughput": 88,
                        "issue_engagement": 90,
                    },
                ),
                contributor_sustainability=DimensionScore(
                    score=78,
                    grade="B",
                    details={
                        "bus_factor": 72,
                        "contributor_diversity": 81,
                        "new_contributor_inflow": 80,
                    },
                ),
                release_engineering=DimensionScore(
                    score=85,
                    grade="A",
                    details={
                        "release_frequency": 90,
                        "semantic_versioning": 82,
                        "release_stability": 83,
                    },
                ),
                governance=DimensionScore(
                    score=76,
                    grade="B",
                    details={
                        "license_clarity": 100,
                        "contributing_docs": 60,
                        "code_of_conduct": 52,
                    },
                ),
                maintenance=DimensionScore(
                    score=74,
                    grade="B",
                    details={
                        "issue_response_time": 70,
                        "pr_merge_time": 78,
                        "stale_issue_ratio": 74,
                    },
                ),
                adoption_popularity=DimensionScore(
                    score=80,
                    grade="B",
                    details={
                        "star_growth": 92,
                        "fork_growth": 78,
                        "dependent_count": 70,
                    },
                ),
            ),
        ),
        ai_report=AIReport(
            summary="React는 전반적으로 건강한 오픈소스 프로젝트입니다.",
            strengths=[
                "커밋 활동이 매우 활발하며 기여자 수가 풍부합니다.",
                "라이선스가 명확하게 명시되어 있습니다.",
                "CI/CD 파이프라인이 잘 구성되어 있습니다.",
            ],
            improvements=[
                "CONTRIBUTING.md 파일을 추가하여 외부 기여자의 참여를 유도하세요.",
                "최근 30일간 미응답 이슈 비율이 높습니다. 이슈 트리아지 프로세스를 도입하세요.",
                "릴리즈 주기가 불규칙합니다. 정기 릴리즈 일정을 수립하는 것을 권장합니다.",
            ],
        ),
    )


@router.post(
    "/analyze",
    response_model=HealthReport,
    summary="Analyse a GitHub repository's open-source health",
)
async def analyze(request: AnalyzeRequest) -> HealthReport:
    """Return a `HealthReport` for the requested repository.

    Currently returns a static mock so the frontend can iterate without
    blocking on the analysis pipeline. The mock is replaced by a call to
    `app.services.analysis_service` in Phase G once the engine interface
    is settled with 김나경.
    """
    return _build_mock_report(request)
