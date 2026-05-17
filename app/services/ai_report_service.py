"""Gemini-backed AI report generation.

Produces the narrative `AIReport` (summary + strengths + improvements)
that accompanies the numeric health score in the analyze response.
Phase G will pass the real `HealthScore` into a Gemini prompt and parse
the structured response; this skeleton returns a fixed report so the
upstream wiring can be developed and tested first.
"""

from __future__ import annotations

from app.schemas.response import AIReport, HealthScore


class AIReportService:
    """Generate an `AIReport` for a scored repository.

    The real implementation will:
      1. Render `health_score` into a Gemini prompt template.
      2. Call `google.generativeai` with `settings.gemini_api_key`.
      3. Parse the structured JSON response into `AIReport`.

    For now `generate` returns a placeholder so the rest of the request
    pipeline (route → analysis → AI report → response) can be exercised
    without a network round-trip.
    """

    async def generate(self, health_score: HealthScore) -> AIReport:
        """Return an `AIReport` derived from `health_score`."""
        return self._mock_report()

    @staticmethod
    def _mock_report() -> AIReport:
        return AIReport(
            summary="전반적으로 건강한 오픈소스 프로젝트로 평가됩니다.",
            strengths=[
                "커밋 활동이 활발하며 기여자 수가 풍부합니다.",
                "라이선스가 명확하게 명시되어 있습니다.",
                "릴리즈 운영 체계가 안정적으로 갖춰져 있습니다.",
            ],
            improvements=[
                "CONTRIBUTING.md 파일을 추가하여 외부 기여자의 참여를 유도하세요.",
                "최근 30일간 미응답 이슈 비율이 높습니다. 이슈 트리아지 프로세스를 도입하세요.",
                "릴리즈 주기가 불규칙합니다. 정기 릴리즈 일정을 수립하는 것을 권장합니다.",
            ],
        )
