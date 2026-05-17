"""Unit tests for the GitHub rate-limit header parser."""

from datetime import datetime, timezone

import httpx

from app.utils.rate_limiter import parse_rate_limit


def _response_with_headers(headers: dict[str, str]) -> httpx.Response:
    return httpx.Response(status_code=200, headers=headers)


def test_parse_rate_limit_extracts_limit_remaining_and_reset() -> None:
    response = _response_with_headers(
        {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4321",
            "X-RateLimit-Reset": "1700000000",
        }
    )

    status = parse_rate_limit(response)

    assert status is not None
    assert status.limit == 5000
    assert status.remaining == 4321
    assert status.reset_at == datetime.fromtimestamp(1700000000, tz=timezone.utc)
    assert status.is_exhausted is False


def test_parse_rate_limit_flags_exhaustion_when_remaining_is_zero() -> None:
    response = _response_with_headers(
        {
            "X-RateLimit-Limit": "60",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1700000000",
        }
    )

    status = parse_rate_limit(response)

    assert status is not None
    assert status.is_exhausted is True


def test_parse_rate_limit_returns_none_without_headers() -> None:
    """Non-GitHub or error responses don't carry the headers; parser no-ops."""
    response = _response_with_headers({})
    assert parse_rate_limit(response) is None


def test_seconds_until_reset_clamps_to_zero_for_past_resets() -> None:
    response = _response_with_headers(
        {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4321",
            "X-RateLimit-Reset": "1700000000",
        }
    )

    status = parse_rate_limit(response)
    assert status is not None

    now = datetime.fromtimestamp(1700000100, tz=timezone.utc)
    assert status.seconds_until_reset(now=now) == 0.0
