"""GitHub URL parsing + repository metadata helper.

Standalone utility: parses GitHub URLs into `(owner, repo)` and can fetch
basic repo metadata via `GitHubClient`. The current diagnose flow does its
own GitHub fetching inside the vendored pipeline, so this module is not on
the request path today; `parse_repo_url` is kept (and tested) as a reusable
helper and an entry point for future response enrichment (stars/forks/etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.utils.github_client import GitHubClient

_GITHUB_URL_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)


class InvalidGitHubURLError(ValueError):
    """Raised when a string is not a recognisable github.com repository URL."""


@dataclass(frozen=True)
class RepoMetadata:
    """Subset of GitHub repo fields surfaced to the analysis pipeline."""

    name: str
    owner: str
    url: str
    stars: int
    forks: int
    language: str | None


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    """Split a github.com URL into `(owner, repo)`.

    Accepts trailing `.git` and optional trailing slash. Raises
    `InvalidGitHubURLError` for anything that doesn't match — callers
    surface that as a 400 to the client.
    """
    match = _GITHUB_URL_PATTERN.match(repo_url.strip())
    if not match:
        raise InvalidGitHubURLError(f"Not a GitHub repository URL: {repo_url!r}")
    return match.group("owner"), match.group("repo")


class GitHubService:
    """High-level GitHub operations used by the analysis flow."""

    def __init__(self, client: GitHubClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> GitHubService:
        if self._client is None:
            self._client = GitHubClient()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_repo_metadata(self, repo_url: str) -> RepoMetadata:
        """Fetch the repo's public metadata from `GET /repos/{owner}/{repo}`."""
        owner, repo = parse_repo_url(repo_url)
        if self._client is None:
            raise RuntimeError("GitHubService must be used as an async context manager")
        payload = await self._client.get_json(f"/repos/{owner}/{repo}")
        return RepoMetadata(
            name=payload["name"],
            owner=payload["owner"]["login"],
            url=payload["html_url"],
            stars=payload.get("stargazers_count", 0),
            forks=payload.get("forks_count", 0),
            language=payload.get("language"),
        )
