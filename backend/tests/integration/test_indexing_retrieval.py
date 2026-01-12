"""Live schema indexing + retrieval against the demo database.

Uses the deterministic StubEmbedder (no model download) so assertions are stable.
Indexes the demo DB through SchemaIndexService, then checks the GET schema
endpoint and the RetrievalService seed/expansion behaviour.
"""

from __future__ import annotations

import uuid

import pytest

from app.drivers import ConnectionCredentials
from app.services.retrieval_service import RetrievalService
from app.services.schema_index_service import SchemaIndexService
from tests.fixtures.stub_embedder import StubEmbedder
from tests.integration.conftest import reg_json, requires_live_stack

pytestmark = [requires_live_stack, pytest.mark.asyncio]

DEMO = ConnectionCredentials(
    host="127.0.0.1",
    port=5433,
    database="demo",
    username="querymind_reader",
    password="querymind_reader",
)


async def _make_connection(client) -> tuple[str, str]:
    """Register + create a demo connection. Returns (connection_id, csrf)."""
    reg = await client.post(
        "/auth/register",
        json=reg_json(email=f"idx-{uuid.uuid4().hex[:12]}@example.com", password="indexing-pw-1"),
    )
    csrf = reg.json()["csrf_token"]
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
        headers={"X-CSRF-Token": csrf},
    )
    return created.json()["id"], csrf


async def _index(connection_id: str) -> int:
    from app.database.engine import get_rw_session_factory

    async with get_rw_session_factory()() as db:
        return await SchemaIndexService(db, StubEmbedder()).index(uuid.UUID(connection_id), DEMO)


async def test_index_populates_tables_columns_and_edges(app_client):
    conn_id, _ = await _make_connection(app_client)
    count = await _index(conn_id)
    assert count == 4  # customers, products, orders, order_items

    schema = await app_client.get(f"/connections/{conn_id}/schema")
    assert schema.status_code == 200
    body = schema.json()
    assert body["index_status"] == "ready"
    names = {t["name"] for t in body["tables"]}
    assert names == {"customers", "products", "orders", "order_items"}

    # order_items -> orders and order_items -> products FK edges were captured.
    fk_pairs = {(f["from_table"], f["to_table"]) for f in body["fks"]}
    assert ("order_items", "orders") in fk_pairs
    assert ("order_items", "products") in fk_pairs

    # Columns carry PK/FK flags.
    orders = next(t for t in body["tables"] if t["name"] == "orders")
    assert any(c["name"] == "id" and c["is_pk"] for c in orders["columns"])
    assert any(c["name"] == "customer_id" and c["is_fk"] for c in orders["columns"])


async def test_retrieval_seeds_and_fk_expands(app_client):
    conn_id, _ = await _make_connection(app_client)
    await _index(conn_id)

    from app.database.engine import get_rw_session_factory

    async with get_rw_session_factory()() as db:
        svc = RetrievalService(db, StubEmbedder())
        result = await svc.retrieve(uuid.UUID(conn_id), "total order amount per customer", seed_k=2)

    retrieved = {t.name for t in result.tables}
    # 'orders' must surface (lexical + vector on order/amount/customer tokens).
    assert "orders" in retrieved
    # FK expansion pulls in neighbours so JOINs are possible.
    assert "customers" in retrieved or "order_items" in retrieved
    assert any(t.via == "fk-expand" for t in result.tables)

    # A formatted, tiered, budget-bounded schema block is produced.
    assert "TABLE orders" in result.formatted_schema
    assert result.token_estimate > 0
    assert result.tables[0].tier == 1


async def test_retrieval_empty_for_unindexed_connection(app_client):
    conn_id, _ = await _make_connection(app_client)  # not indexed
    from app.database.engine import get_rw_session_factory

    async with get_rw_session_factory()() as db:
        result = await RetrievalService(db, StubEmbedder()).retrieve(uuid.UUID(conn_id), "anything")
    assert result.tables == []
    assert result.formatted_schema == ""
