"""Shared test configuration.

* The bearer-token suites run with the HttpOnly session cookie switched off, so that the shared TestClient's cookie
  jar never turns an intentionally anonymous request into an authenticated one. The cookie flow itself is covered
  in test_v3.py with a dedicated client.
* The in-memory rate limiter is reset before every test (all requests come from the same test client IP).
"""
import os

os.environ.setdefault("AUTH_COOKIE_ENABLED", "false")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from app.core.ratelimit import reset

    reset()
    yield
