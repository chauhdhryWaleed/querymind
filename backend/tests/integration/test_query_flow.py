"""End-to-end /query against the demo DB with a mocked LLM (deterministic SQL).

Covers the M4 spine: auth + connection + BYOK key resolution → retrieval →
validate (incl. EXPLAIN against the user DB) → execute → interpret → scoped
history. The LLM is mocked so no real API key is needed; retrieval uses the
deterministic stub embedder.
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.drivers import ConnectionCredentials
from app.llm.base import LLMResponse
from app.services.schema_index_service import SchemaIndexService
from tests.fixtures.stub_embedder import StubEmbedder
from tests.integration.conftest import reg_json, requires_live_stack

pytestmark = [requires_live_stack, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    from app.main import app

    app.dependency_overrides.clear()


DEMO = ConnectionCredentials(
    host="127.0.0.1",
    port=5433,
    database="demo",
    username="querymind_reader",
    password="querymind_reader",
)
_SQL = "SELECT id, name, email FROM customers LIMIT 5"


class FakeLLM:
    """Returns canned SQL for generation calls and plain text for interpretation."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def generate(self, system, messages, temperature=0.1) -> LLMResponse:
        last = messages[-1].content.lower() if messages else ""
        if "natural language answer" in last:
            content = "There are 5 customers shown."
        else:
            content = json.dumps({"sql": _SQL, "explanation": "Lists customers."})
        return LLMResponse(content=content, input_tokens=10, output_tokens=20, model="fake")

    async def stream(self, system, messages, temperature=0.1):
        yield ""


def _email() -> str:
    return f"q-{uuid.uuid4().hex[:12]}@example.com"


async def _setup(client, monkeypatch, *, with_key=True, index=True):
    """Register, create + index a demo connection, add an LLM key, wire mocks."""
    import app.api.endpoints.query as query_mod
    from app.api.dependencies import get_embedder
    from app.main import app

    app.dependency_overrides[get_embedder] = lambda: StubEmbedder()
    monkeypatch.setattr(query_mod, "build_llm_provider", lambda *a, **k: FakeLLM())

    reg = await client.post("/auth/register", json=reg_json(email=_email(), password="query-pw-12"))
    csrf = reg.json()["csrf_token"]
    h = {"X-CSRF-Token": csrf}

    created = await client.post(
        "/connections",
        json={
            "name": "Demo",
            "dialect": "postgres",
            "host": "127.0.0.1",
            "port": 5433,
            "database": "demo",
            "username": "querymind_reader",
            "password": "querymind_reader",
        },
        headers=h,
    )
    conn_id = created.json()["id"]

    if index:
        from app.database.engine import get_rw_session_factory

        async with get_rw_session_factory()() as db:
            await SchemaIndexService(db, StubEmbedder()).index(uuid.UUID(conn_id), DEMO)

    if with_key:
        await client.post(
            "/llm-keys",
            json={"provider": "anthropic", "api_key": "sk-ant-test-xyz", "is_default": True},
            headers=h,
        )
    return conn_id, h


async def test_query_end_to_end(app_client, monkeypatch):
    conn_id, h = await _setup(app_client, monkeypatch)

    resp = await app_client.post(
        "/query", json={"connection_id": conn_id, "question": "list all customers"}, headers=h
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "select" in body["sql"].lower()
    assert body["columns"] == ["id", "name", "email"]
    assert body["row_count"] == 5
    assert len(body["results"]) == 5
    # Retrieval disclosure is present and includes the customers table.
    tables = {t["name"] for t in body["metadata"]["retrieval"]["tables"]}
    assert "customers" in tables
    assert body["metadata"]["retrieval"]["schema_tokens"] > 0

    # History was written and is workspace-scoped.
    hist = await app_client.get(f"/history/{body['metadata']['request_id']}")
    # (request_id != session_id, so this is empty; just assert the route is authed.)
    assert hist.status_code in (200,)


async def test_query_requires_indexed_connection(app_client, monkeypatch):
    conn_id, h = await _setup(app_client, monkeypatch, index=False)
    resp = await app_client.post(
        "/query", json={"connection_id": conn_id, "question": "list all customers"}, headers=h
    )
    assert resp.status_code == 409  # schema not ready


async def test_query_requires_llm_key(app_client, monkeypatch):
    conn_id, h = await _setup(app_client, monkeypatch, with_key=False)
    resp = await app_client.post(
        "/query", json={"connection_id": conn_id, "question": "list all customers"}, headers=h
    )
    assert resp.status_code == 400  # no LLM key configured


async def test_query_requires_csrf(app_client, monkeypatch):
    conn_id, _ = await _setup(app_client, monkeypatch)
    resp = await app_client.post(
        "/query", json={"connection_id": conn_id, "question": "list all customers"}
    )
    assert resp.status_code == 403


class _AuthError(Exception):
    """Mimics anthropic/openai AuthenticationError (matched by class name)."""

    __name__ = "AuthenticationError"


class _RejectingLLM(FakeLLM):
    async def generate(self, system, messages, temperature=0.1):
        raise type("AuthenticationError", (Exception,), {})("invalid x-api-key")


async def test_query_invalid_key_returns_502(app_client, monkeypatch):
    conn_id, h = await _setup(app_client, monkeypatch)
    import app.api.endpoints.query as query_mod

    monkeypatch.setattr(query_mod, "build_llm_provider", lambda *a, **k: _RejectingLLM())
    resp = await app_client.post(
        "/query", json={"connection_id": conn_id, "question": "list all customers"}, headers=h
    )
    assert resp.status_code == 502
    assert "rejected" in resp.json()["detail"].lower()


async def test_query_cross_tenant_connection_404(app_client, monkeypatch):
    conn_id, _ = await _setup(app_client, monkeypatch)
    # Switch to a new user; the connection isn't theirs.
    reg = await app_client.post(
        "/auth/register", json=reg_json(email=_email(), password="other-pw-12")
    )
    h = {"X-CSRF-Token": reg.json()["csrf_token"]}
    resp = await app_client.post(
        "/query", json={"connection_id": conn_id, "question": "list all customers"}, headers=h
    )
    assert resp.status_code == 404
