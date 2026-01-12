"""Integration fixtures: a lifespan-managed app client bound to a live Postgres
+ Redis. Skips automatically when no test database is configured.

Point it at the dev compose stack (or a testcontainers-provisioned DB) via:
    TEST_DATABASE_URL=postgresql+asyncpg://querymind:querymind@localhost:5433/querymind
    TEST_REDIS_URL=redis://localhost:6380/0
The target DB must already be migrated to head.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

_DB = os.environ.get("TEST_DATABASE_URL")
_REDIS = os.environ.get("TEST_REDIS_URL")

requires_live_stack = pytest.mark.skipif(
    not (_DB and _REDIS),
    reason="set TEST_DATABASE_URL and TEST_REDIS_URL to run live integration tests",
)


def reg_json(email: str | None = None, password: str = "test-password-123", **overrides) -> dict:
    """A complete /auth/register payload with the now-required profile fields.
    Generates a unique email so repeated registrations don't collide."""
    uid = uuid.uuid4().hex[:12]
    payload = {
        "email": email or f"user-{uid}@example.com",
        "password": password,
        "first_name": "Test",
        "last_name": "User",
        "job_role": "Data Analyst",
        "company": "Acme Inc",
        "country": "United States",
        "use_case": "Ad-hoc analytics",
    }
    payload.update(overrides)
    return payload


def login_json(email: str, password: str) -> dict:
    """A /auth/login payload."""
    return {"email": email, "password": password}


@pytest_asyncio.fixture
async def app_client():
    # Configure settings to target the live stack before the app is built.
    os.environ["DATABASE_URL"] = _DB or ""
    os.environ["DATABASE_URL_READONLY"] = _DB or ""
    os.environ["REDIS_URL"] = _REDIS or ""
    os.environ["OTEL_ENABLE_INSTRUMENTATION"] = "false"
    os.environ["ENVIRONMENT"] = "development"  # cookie_secure off for http test client

    from app.config.settings import get_settings

    get_settings.cache_clear()

    # Tests hammer /auth/* far past the 5/15min production limit; disable it.
    from app.api.rate_limit import limiter

    limiter.enabled = False

    from app.main import app

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client
