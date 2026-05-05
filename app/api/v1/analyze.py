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
    """Construct a deterministic mock report mirroring the README example.

    Echoes the requested URL inside `Repository.url` so the frontend can
    verify round-trip wiring during integration without depending on the
    real GitHub fetch.
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
                        "activity_volume": 95,
                        "responsiveness": 88,
                        "engagement_quality": 90,
                    },
                ),
                sustainability=DimensionScore(
                    score=78,
                    grade="B",
                    details={
                        "contributor_structure": 72,
                        "diversity": 81,
                        "activity_stability": 80,
                    },
                ),
                code_quality=DimensionScore(
                    score=85,
                    grade="A",
                    details={
                        "engineering_practice": 90,
                        "defect_signals": 82,
                        "security_signals": 83,
                    },
                ),
                governance=DimensionScore(
                    score=76,
                    grade="B",
                    details={
                        "legal_compliance": 100,
                        "governance_structure": 52,
                    },
                ),
                maturity=DimensionScore(
                    score=80,
                    grade="B",
                    details={
                        "release_engineering": 85,
                        "adoption_popularity": 92,
                        "lifecycle_scale": 63,
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
