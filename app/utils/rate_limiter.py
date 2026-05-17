"""GitHub REST API rate-limit helpers.

GitHub returns the caller's quota state in three response headers:

    X-RateLimit-Limit       total requests allowed in the current window
    X-RateLimit-Remaining   requests still available
    X-RateLimit-Reset       UNIX timestamp when the window resets

This module parses those headers into a typed `RateLimitStatus` and lets
callers query whether the limit has been exhausted. Actual back-off /
sleep behaviour is left to the calling service.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass(frozen=True)
class RateLimitStatus:
    """Snapshot of GitHub's reported rate-limit state for the current token."""

    limit: int
    remaining: int
    reset_at: datetime

    @property
    def is_exhausted(self) -> bool:
        """True when no further requests can be made until `reset_at`."""
        return self.remaining <= 0

    def seconds_until_reset(self, now: datetime | None = None) -> float:
        """Seconds remaining until the rate-limit window resets (>= 0)."""
        current = now or datetime.now(timezone.utc)
        delta = (self.reset_at - current).total_seconds()
        return max(0.0, delta)


def parse_rate_limit(response: httpx.Response) -> RateLimitStatus | None:
    """Return the rate-limit snapshot embedded in a GitHub response.

    Returns `None` if the response did not include the standard headers
    (e.g. an error reply or a non-GitHub host), so callers can no-op
    instead of branching on three separate `None` checks.
    """
    headers = response.headers
    raw_limit = headers.get("X-RateLimit-Limit")
    raw_remaining = headers.get("X-RateLimit-Remaining")
    raw_reset = headers.get("X-RateLimit-Reset")
    if raw_limit is None or raw_remaining is None or raw_reset is None:
        return None
    return RateLimitStatus(
        limit=int(raw_limit),
        remaining=int(raw_remaining),
        reset_at=datetime.fromtimestamp(int(raw_reset), tz=timezone.utc),
    )
