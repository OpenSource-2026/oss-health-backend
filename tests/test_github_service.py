"""Unit tests for GitHubService URL parsing."""

import pytest

from app.services.github_service import InvalidGitHubURLError, parse_repo_url


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://github.com/facebook/react", ("facebook", "react")),
        ("http://github.com/facebook/react", ("facebook", "react")),
        ("https://github.com/facebook/react/", ("facebook", "react")),
        ("https://github.com/facebook/react.git", ("facebook", "react")),
        ("  https://github.com/owner-1/repo_2  ", ("owner-1", "repo_2")),
    ],
)
def test_parse_repo_url_accepts_canonical_forms(url: str, expected: tuple[str, str]) -> None:
    assert parse_repo_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/facebook/react",
        "https://github.com/facebook",
        "not-a-url",
        "",
    ],
)
def test_parse_repo_url_rejects_non_repo_urls(url: str) -> None:
    with pytest.raises(InvalidGitHubURLError):
        parse_repo_url(url)
