"""Unit tests for table-signature building and drift hashing (no DB)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.schema_index_service import build_table_signature, compute_schema_hash


@dataclass
class _Col:
    name: str


@dataclass
class _Table:
    schema_name: str
    name: str
    kind: str
    row_count: int | None
    description: str | None
    columns: list


@dataclass
class _Fk:
    from_schema: str
    from_table: str
    from_column: str
    to_schema: str
    to_table: str
    to_column: str


@dataclass
class _Schema:
    tables: list
    fks: list


def _orders():
    return _Table(
        "public",
        "orders",
        "table",
        125000,
        "main orders fact table",
        [_Col("id"), _Col("customer_id"), _Col("total_amount"), _Col("status")],
    )


def test_signature_includes_core_fields():
    fk_out = _Fk("public", "orders", "customer_id", "public", "customers", "id")
    fk_in = _Fk("public", "order_items", "order_id", "public", "orders", "id")
    sig = build_table_signature(_orders(), [fk_out], [fk_in])
    assert "[table: orders]" in sig
    assert "purpose: main orders fact table" in sig
    assert "columns: id, customer_id, total_amount, status" in sig
    assert "references: customer_id -> customers.id" in sig
    assert "referenced by: order_items.order_id" in sig
    assert "row_count: ~125000" in sig


def test_signature_omits_optional_sections_when_empty():
    t = _Table("public", "regions", "table", None, None, [_Col("id"), _Col("name")])
    sig = build_table_signature(t, [], [])
    assert "references:" not in sig
    assert "referenced by:" not in sig
    assert "row_count:" not in sig


def test_schema_hash_changes_with_structure():
    base = _Schema([_orders()], [])
    h1 = compute_schema_hash(base)
    # Same structure → same hash.
    assert h1 == compute_schema_hash(_Schema([_orders()], []))
    # An added column changes it.
    wider = _orders()
    wider.columns.append(_Col("region"))
    assert h1 != compute_schema_hash(_Schema([wider], []))
