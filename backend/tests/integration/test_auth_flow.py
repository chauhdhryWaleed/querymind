"""End-to-end auth flow against a live Postgres + Redis.

Covers: register -> /me -> workspace rename (CSRF) -> logout -> login ->
password reset -> login with the new password. Each test uses a unique email so
runs don't collide.
"""

from __future__ import annotations

import uuid

import pytest

from tests.integration.conftest import login_json, reg_json, requires_live_stack

pytestmark = [requires_live_stack, pytest.mark.asyncio]


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


async def test_register_me_logout_login(app_client):
    email = _email()
    pw = "correct-horse-battery"

    # Register -> 201, sets cookies, returns workspace + csrf token.
    r = await app_client.post("/auth/register", json=reg_json(email=email, password=pw))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == email
    assert body["workspace"]["role"] == "owner"
    assert app_client.cookies.get("t2s_session")

    # /me reflects the authenticated user + their workspace.
    me = await app_client.get("/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == email
    assert len(me.json()["workspaces"]) == 1

    # Logout clears the session; /me now 401.
    out = await app_client.post("/auth/logout")
    assert out.status_code == 204
    assert (await app_client.get("/me")).status_code == 401

    # Login again works (by email).
    li = await app_client.post("/auth/login", json=login_json(email, pw))
    assert li.status_code == 200
    assert (await app_client.get("/me")).status_code == 200


async def test_duplicate_email_rejected(app_client):
    payload = reg_json()
    assert (await app_client.post("/auth/register", json=payload)).status_code == 201
    dup = await app_client.post("/auth/register", json=payload)
    assert dup.status_code == 409


async def test_login_wrong_password_is_401(app_client):
    email = _email()
    await app_client.post("/auth/register", json=reg_json(email=email, password="right-password-1"))
    await app_client.post("/auth/logout")
    bad = await app_client.post("/auth/login", json=login_json(email, "wrong-password"))
    assert bad.status_code == 401
    # Same response for an unknown identifier (no enumeration).
    unknown = await app_client.post("/auth/login", json=login_json(_email(), "whatever-here"))
    assert unknown.status_code == 401


async def test_workspace_rename_requires_csrf(app_client):
    email = _email()
    reg = await app_client.post(
        "/auth/register", json=reg_json(email=email, password="rename-me-please")
    )
    csrf = reg.json()["csrf_token"]
    ws_id = reg.json()["workspace"]["id"]

    # Without CSRF header -> 403.
    no_csrf = await app_client.patch(f"/workspaces/{ws_id}", json={"name": "Analytics"})
    assert no_csrf.status_code == 403

    # With CSRF header -> renamed.
    ok = await app_client.patch(
        f"/workspaces/{ws_id}", json={"name": "Analytics"}, headers={"X-CSRF-Token": csrf}
    )
    assert ok.status_code == 200
    assert ok.json()["name"] == "Analytics"


async def test_password_reset_flow(app_client):
    email = _email()
    old_pw = "old-password-123"
    await app_client.post("/auth/register", json=reg_json(email=email, password=old_pw))

    # Request a reset; endpoint always 202. Grab the raw token from the service.
    req = await app_client.post("/auth/password-reset/request", json={"email": email})
    assert req.status_code == 202

    from sqlalchemy import select

    from app.config.settings import get_settings
    from app.database.engine import get_rw_session_factory
    from app.models.user import EmailToken

    # Re-issue a token deterministically by calling the service directly would be
    # cleaner, but here we assert a reset token row exists for the user.
    async with get_rw_session_factory()() as db:
        from app.models.user import User

        user = await db.scalar(select(User).where(User.email == email))
        token_row = await db.scalar(
            select(EmailToken).where(EmailToken.user_id == user.id, EmailToken.purpose == "reset")
        )
        assert token_row is not None
        assert token_row.consumed_at is None

    get_settings()  # touch settings (kept for parity with app config)


async def test_password_reset_complete_changes_password(app_client):
    """Drive the reset end-to-end via the service to get the raw token, then
    verify the new password works and the old one does not."""
    from app.config.settings import get_settings
    from app.database.engine import get_rw_session_factory
    from app.services.audit_service import AuditService
    from app.services.auth_service import AuthService
    from app.services.email_service import EmailService

    email = _email()
    old_pw, new_pw = "old-secret-789", "fresh-secret-012"
    await app_client.post("/auth/register", json=reg_json(email=email, password=old_pw))

    settings = get_settings()
    from app.main import app as _app

    redis = _app.state.redis
    async with get_rw_session_factory()() as db:
        svc = AuthService(db, redis, settings, EmailService(settings), AuditService(db))
        token = await svc.request_password_reset(email)
        assert token is not None
        ok = await svc.complete_password_reset(token, new_pw)
        assert ok is True

    # Old password rejected, new password accepted.
    await app_client.post("/auth/logout")
    assert (
        await app_client.post("/auth/login", json=login_json(email, old_pw))
    ).status_code == 401
    assert (
        await app_client.post("/auth/login", json=login_json(email, new_pw))
    ).status_code == 200
