"""Minimal in-process TTL cache.

Used to memoise repository diagnoses so repeated requests for the same repo
return instantly and avoid re-hitting the GitHub API — the response-caching
mitigation called for in the proposal's rate-limit risk plan (§3.6) and the
data team's `API_CONTRACT.md`.

In-memory and single-process by design (no Redis dependency): the API is
accessed from a single event loop, so plain dict access needs no locking.
For a multi-replica deployment this would move to a shared store.
"""

from __future__ import annotations

import time
from typing import Any


class TTLCache:
    """A dict-backed cache where entries expire after `ttl` seconds."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        """Return the cached value for `key`, or None if missing/expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if time.monotonic() - stored_at > self._ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        """Store `value` under `key` with the current timestamp."""
        self._store[key] = (time.monotonic(), value)

    def clear(self) -> None:
        """Drop all cached entries (used by tests)."""
        self._store.clear()
