"""
Integration tests for SqlExecutor.
These tests run against a real PostgreSQL instance.
Set DATABASE_URL_READONLY in env or use testcontainers.
Skip if no DB available.
"""

import pytest

from app.executors.sql_executor import SqlExecutor

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_limit_injection(sample_schema: dict) -> None:
    """SqlExecutor._inject_limit adds LIMIT when absent."""
    executor = SqlExecutor(max_rows=10)
    sql = "SELECT id FROM orders"
    bounded = executor._inject_limit(sql)
    assert "LIMIT" in bounded.upper()
    assert "10" in bounded


@pytest.mark.asyncio
async def test_limit_cap(sample_schema: dict) -> None:
    """SqlExecutor._inject_limit caps an existing LIMIT that exceeds max_rows."""
    executor = SqlExecutor(max_rows=50)
    sql = "SELECT id FROM orders LIMIT 9999"
    bounded = executor._inject_limit(sql)
    assert "9999" not in bounded
    assert "50" in bounded


@pytest.mark.asyncio
async def test_existing_small_limit_preserved(sample_schema: dict) -> None:
    """A LIMIT smaller than max_rows is left unchanged."""
    executor = SqlExecutor(max_rows=1000)
    sql = "SELECT id FROM orders LIMIT 5"
    bounded = executor._inject_limit(sql)
    assert "5" in bounded
