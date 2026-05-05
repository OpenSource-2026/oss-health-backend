"""Shared pytest fixtures and environment setup.

Required environment variables (see `app/config.py`) are seeded here with
dummy values so that `Settings` validation does not fail when running the
test suite without a local `.env` file.
"""

import os

# Seed required env vars before any `app.*` import in test modules.
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
