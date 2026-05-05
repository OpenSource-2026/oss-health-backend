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

    github_token: str = Field(
        ...,
        description="GitHub Personal Access Token used to raise the API rate limit.",
    )
    gemini_api_key: str = Field(
        ...,
        description="Google Gemini API key used to generate AI improvement reports.",
    )
    cors_origins: str = Field(
        default="http://localhost:3000",
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached `Settings` instance.

    Cached so middleware and request handlers reuse the same parsed config
    without re-reading the environment on every call.
    """
    return Settings()
