"""Analysis pipeline orchestration.

Bridges the API layer to the data-pipeline (김나경's ML / feature
engineering module). Currently returns a deterministic mock
`HealthScore` so the API and frontend can develop against the real
response shape; Phase G replaces `_mock_score` with a call into the
pipeline package.

Keeping the call site behind this service means the route handler in
`api/v1/analyze.py` never needs to know whether it is talking to a mock
or the real engine.
"""

from __future__ import annotations

from app.schemas.response import DimensionScore, HealthDimensions, HealthScore
from app.services.github_service import RepoMetadata


class AnalysisService:
    """Run the health-analysis pipeline for a repository.

    The pipeline call is currently mocked. The real implementation will
    accept the `RepoMetadata` plus a deeper feature payload (commits,
    issues, PRs, releases) collected by `GitHubService` and return the
    same `HealthScore` shape.
    """

    async def score(self, repo: RepoMetadata) -> HealthScore:
        """Return a `HealthScore` for the given repository."""
        return self._mock_score()

    @staticmethod
    def _mock_score() -> HealthScore:
        """Deterministic placeholder score covering all six dimensions."""
        return HealthScore(
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
        )
