"""End-to-end connection + BYOK key management against a live stack.

The connection test dials the separate `demo` database (read-only role) exposed
on the host at 127.0.0.1:5433.
"""

from __future__ import annotations

import uuid

import pytest

from tests.integration.conftest import reg_json, requires_live_stack

pytestmark = [requires_live_stack, pytest.mark.asyncio]

# The demo DB as reachable from the host-run test process.
DEMO = {
    "host": "127.0.0.1",
    "port": 5433,
    "database": "demo",
    "username": "querymind_reader",
    "password": "querymind_reader",
}


def _email() -> str:
    return f"conn-{uuid.uuid4().hex[:12]}@example.com"


async def _register(client) -> str:
    """Register a fresh user; return the CSRF token."""
    r = await client.post(
        "/auth/register", json=reg_json(email=_email(), password="connections-pw-123")
    )
    assert r.status_code == 201, r.text
    return r.json()["csrf_token"]


async def test_connection_crud_and_test(app_client):
    csrf = await _register(app_client)
    h = {"X-CSRF-Token": csrf}

    # Create.
    payload = {"name": "Demo DB", "dialect": "postgres", **DEMO}
    created = await app_client.post("/connections", json=payload, headers=h)
    assert created.status_code == 201, created.text
    body = created.json()
    conn_id = body["id"]
    assert body["host"] == DEMO["host"]
    assert body["index_status"] == "pending"
    assert "password" not in body  # never returned

    # List shows it, still no password field.
    listed = await app_client.get("/connections")
    assert listed.status_code == 200
    assert any(c["id"] == conn_id for c in listed.json())
    assert all("password" not in c for c in listed.json())

    # Test connectivity against the real demo DB.
    test = await app_client.post(f"/connections/{conn_id}/test", headers=h)
    assert test.status_code == 200, test.text
    assert test.json()["ok"] is True
    assert "PostgreSQL" in (test.json()["server_version"] or "")

    # Update the name; password omitted -> unchanged.
    upd = await app_client.patch(
        f"/connections/{conn_id}", json={"name": "Renamed Demo"}, headers=h
    )
    assert upd.status_code == 200
    assert upd.json()["name"] == "Renamed Demo"

    # Re-test still works (password preserved through the update).
    assert (await app_client.post(f"/connections/{conn_id}/test", headers=h)).json()["ok"] is True

    # Delete.
    assert (await app_client.delete(f"/connections/{conn_id}", headers=h)).status_code == 204
    assert (await app_client.get(f"/connections/{conn_id}")).status_code == 404


async def test_test_bad_host_warns_but_save_succeeds(app_client):
    csrf = await _register(app_client)
    h = {"X-CSRF-Token": csrf}
    bad = {**DEMO, "host": "10.255.255.1", "port": 5999}
    created = await app_client.post(
        "/connections", json={"name": "Unreachable", "dialect": "postgres", **bad}, headers=h
    )
    assert created.status_code == 201  # save succeeds even if it won't connect
    conn_id = created.json()["id"]
    test = await app_client.post(f"/connections/{conn_id}/test", headers=h)
    assert test.status_code == 200
    assert test.json()["ok"] is False  # warn, don't block


async def test_create_requires_csrf(app_client):
    await _register(app_client)
    no_csrf = await app_client.post(
        "/connections", json={"name": "X", "dialect": "postgres", **DEMO}
    )
    assert no_csrf.status_code == 403


async def test_tenant_isolation(app_client):
    # User A creates a connection.
    csrf_a = await _register(app_client)
    created = await app_client.post(
        "/connections",
        json={"name": "A's DB", "dialect": "postgres", **DEMO},
        headers={"X-CSRF-Token": csrf_a},
    )
    conn_id = created.json()["id"]

    # User B (same client, re-register switches the session cookie) can't see it.
    await _register(app_client)
    assert (await app_client.get(f"/connections/{conn_id}")).status_code == 404
    assert all(c["id"] != conn_id for c in (await app_client.get("/connections")).json())


async def test_llm_key_crud(app_client):
    csrf = await _register(app_client)
    h = {"X-CSRF-Token": csrf}

    created = await app_client.post(
        "/llm-keys",
        json={
            "provider": "anthropic",
            "label": "primary",
            "api_key": "sk-ant-secret-7f3a",
            "is_default": True,
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["key_hint"].endswith("7f3a")
    assert "api_key" not in body
    assert body["is_default"] is True
    key_id = body["id"]

    # Second default clears the first.
    second = await app_client.post(
        "/llm-keys",
        json={"provider": "openai", "api_key": "sk-openai-abcd", "is_default": True},
        headers=h,
    )
    assert second.status_code == 201
    keys = {k["id"]: k for k in (await app_client.get("/llm-keys")).json()}
    assert keys[key_id]["is_default"] is False
    assert keys[second.json()["id"]]["is_default"] is True

    # Delete.
    assert (await app_client.delete(f"/llm-keys/{key_id}", headers=h)).status_code == 204
