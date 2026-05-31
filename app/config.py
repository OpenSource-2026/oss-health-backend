"""Application configuration loaded from environment variables.

Settings are read from the process environment, optionally seeded by a local
`.env` file. See `.env.example` for the full list of supported variables.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    github_token: str | None = Field(
        default=None,
        description=(
            "GitHub Personal Access Token used to raise the API rate limit. "
            "Optional: without it the analysis pipeline falls back to "
            "unauthenticated GitHub access (60 req/hour) or a bundled sample."
        ),
    )
    gemini_api_key: str | None = Field(
        default=None,
        description=(
            "Google Gemini API key used to generate the optional AI report. "
            "Optional: when unset the diagnosis is returned without ai_report."
        ),
    )
    gemini_model: str = Field(
        # gemini-1.5-flash retired; 2.0-flash has free-tier limit 0 (needs
        # billing). 2.5-flash works on the free tier. Override via GEMINI_MODEL.
        default="gemini-2.5-flash",
        description=(
            "Gemini model used for the AI report. A flash-tier model is the "
            "default for cost/latency; override via env if it is retired."
        ),
    )
    cors_origins: str = Field(
        # Includes Vite's default dev port (5173) and CRA's (3000) so a local
        # `uvicorn` run is not CORS-blocked by the frontend out of the box.
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed frontend origins.",
    )
    debug: bool = Field(
        default=False,
        description="Enable verbose logging and FastAPI debug mode.",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse `cors_origins` into a list of trimmed origin strings."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @staticmethod
    def _is_real_secret(value: str | None) -> bool:
        """True when a secret is set to a usable value, not a placeholder.

        The `.env.example` ships placeholder strings (e.g.
        `your_gemini_api_key_here`); treat those as "unset" so a fresh clone
        runs in keyless / fixture-fallback mode instead of failing.
        """
        if not value:
            return False
        placeholders = ("your_", "ghp_your", "ci-dummy", "test-")
        return not value.strip().lower().startswith(placeholders)

    @property
    def gemini_enabled(self) -> bool:
        """True when a real Gemini key is configured for AI report generation."""
        return self._is_real_secret(self.gemini_api_key)

    @property
    def github_token_enabled(self) -> bool:
        """True when a real GitHub token is configured for authenticated calls."""
        return self._is_real_secret(self.github_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached `Settings` instance.

    Cached so middleware and request handlers reuse the same parsed config
    without re-reading the environment on every call.
    """
    return Settings()
