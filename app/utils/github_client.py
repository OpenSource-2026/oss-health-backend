"""Async HTTP client wrapper for the GitHub REST API.

Thin layer over `httpx.AsyncClient` that pins the GitHub API base URL,
attaches the configured Personal Access Token, and applies a sensible
default timeout. The wrapper deliberately stays small: parsing and
retry policy live in the services that call it, not here.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings

GITHUB_API_BASE_URL = "https://api.github.com"
DEFAULT_TIMEOUT_SECONDS = 10.0


class GitHubClient:
    """Async GitHub REST API client.

    Use as an async context manager so the underlying connection pool is
    closed deterministically:

        async with GitHubClient() as gh:
            data = await gh.get_json("/repos/facebook/react")
    """

    def __init__(
        self,
        token: str | None = None,
        base_url: str = GITHUB_API_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        resolved_token = token or get_settings().github_token
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {resolved_token}",
        }
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
        )

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """GET `path` and return the raw response (caller handles errors)."""
        return await self._client.get(path, **kwargs)

    async def get_json(self, path: str, **kwargs: Any) -> Any:
        """GET `path` and return parsed JSON, raising for HTTP errors."""
        response = await self.get(path, **kwargs)
        response.raise_for_status()
        return response.json()
