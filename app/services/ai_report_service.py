"""Optional Gemini-backed AI report generation.

Produces the narrative `AIReport` (summary + strengths + improvements) that
*optionally* accompanies a diagnosis. The frontend already derives a
data-based improvement list from the engine's `risk_features`, so this is an
additive enhancement, not a hard dependency:

  - No `GEMINI_API_KEY` configured  → `generate()` returns `None`.
  - Gemini call fails for any reason → `generate()` returns `None`.

In both cases the diagnosis is still returned in full; only the `ai_report`
field is omitted. This keeps the proposal's "AI 개선 제안" feature available
when a key is present without making the core scoring flow depend on it.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anyio

from app.config import get_settings
from app.schemas.diagnosis import AIReport
from app.utils.cache import TTLCache

logger = logging.getLogger(__name__)

# Cache generated reports by repo so re-analysing the same repo within the
# window does not spend another Gemini call (protects the API quota).
_report_cache = TTLCache(3600.0)

_PROMPT_TEMPLATE = """\
당신은 오픈소스 프로젝트 건강도 분석 결과를 해석하는 전문가입니다.
아래 JSON은 '{repo_name}' 저장소에 대한 진단 결과입니다.
종합 점수, 5개 차원별 점수/등급, 차원별 강점(strength_features)과
위험(risk_features) 신호가 들어 있습니다.

이 데이터를 바탕으로 다음 JSON 형식으로만 한국어 응답을 생성하세요. 다른 텍스트는 출력하지 마세요.
{{
  "summary": "프로젝트 건강도에 대한 2~3문장 종합 요약",
  "strengths": ["구체적인 강점 3가지"],
  "improvements": ["구체적이고 실행 가능한 개선 제안 3가지"]
}}

진단 결과:
{diagnosis_json}
"""


class AIReportService:
    """Generate an optional `AIReport` from a diagnosis result."""

    async def generate(self, diagnosis: dict[str, Any]) -> AIReport | None:
        """Return an `AIReport` for the diagnosis, or `None` if unavailable."""
        settings = get_settings()
        if not settings.gemini_enabled:
            logger.info("GEMINI_API_KEY not configured; skipping AI report.")
            return None

        cache_key = str(diagnosis.get("repo_name", ""))
        cached = _report_cache.get(cache_key) if cache_key else None
        if cached is not None:
            return cached

        try:
            report = await anyio.to_thread.run_sync(
                self._generate_sync, diagnosis, settings.gemini_api_key, settings.gemini_model
            )
        except Exception:
            logger.warning("Gemini AI report generation failed; omitting ai_report.", exc_info=True)
            return None

        if cache_key:
            _report_cache.set(cache_key, report)
        return report

    @staticmethod
    def _generate_sync(diagnosis: dict[str, Any], api_key: str, model_name: str) -> AIReport:
        """Blocking Gemini call + response parsing (run in a worker thread)."""
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        prompt = _PROMPT_TEMPLATE.format(
            repo_name=diagnosis.get("repo_name", "the repository"),
            diagnosis_json=json.dumps(diagnosis, ensure_ascii=False),
        )
        response = model.generate_content(prompt)
        payload = _extract_json(response.text)
        return AIReport(
            summary=payload["summary"],
            strengths=list(payload.get("strengths", [])),
            improvements=list(payload.get("improvements", [])),
        )


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the JSON object out of a model reply that may wrap it in fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[len("json"):]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in Gemini response")
    return json.loads(cleaned[start : end + 1])
