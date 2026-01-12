import pytest

from app.validators.schema_check import SchemaValidator
from tests.fixtures.sample_queries import VALID_QUERIES
from tests.fixtures.sample_schema import SAMPLE_SCHEMA


@pytest.fixture
def validator() -> SchemaValidator:
    return SchemaValidator()


@pytest.mark.asyncio
@pytest.mark.parametrize("sql", VALID_QUERIES)
async def test_valid_queries_pass(validator: SchemaValidator, sql: str) -> None:
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert result.passed, f"Expected PASS for: {sql}\nErrors: {result.errors}"


@pytest.mark.asyncio
async def test_unknown_table_fails(validator: SchemaValidator) -> None:
    sql = "SELECT id FROM nonexistent_table LIMIT 10"
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert not result.passed
    assert any("nonexistent_table" in e for e in result.errors)


@pytest.mark.asyncio
async def test_unknown_column_fails(validator: SchemaValidator) -> None:
    sql = "SELECT o.ghost_column FROM orders o LIMIT 10"
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert not result.passed
    assert any("ghost_column" in e for e in result.errors)


@pytest.mark.asyncio
async def test_cte_name_not_flagged_as_unknown_table(validator: SchemaValidator) -> None:
    sql = (
        "WITH customer_lifetime_value AS ("
        "  SELECT o.customer_id, SUM(o.total_amount) AS lifetime_value "
        "  FROM orders o GROUP BY o.customer_id"
        ") "
        "SELECT c.id, c.name, c.email, clv.lifetime_value "
        "FROM customers c "
        "JOIN customer_lifetime_value clv ON c.id = clv.customer_id "
        "ORDER BY clv.lifetime_value DESC LIMIT 10"
    )
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert result.passed, result.errors


@pytest.mark.asyncio
async def test_cte_does_not_mask_real_unknown_table(validator: SchemaValidator) -> None:
    sql = (
        "WITH cte AS (SELECT id FROM ghost_table) "
        "SELECT id FROM cte LIMIT 10"
    )
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert not result.passed
    assert any("ghost_table" in e for e in result.errors)


@pytest.mark.asyncio
async def test_information_schema_query_passes(validator: SchemaValidator) -> None:
    sql = (
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'products'"
    )
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert result.passed, result.errors


@pytest.mark.asyncio
async def test_pg_catalog_query_passes(validator: SchemaValidator) -> None:
    sql = "SELECT relname FROM pg_catalog.pg_class LIMIT 10"
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert result.passed, result.errors


@pytest.mark.asyncio
async def test_unqualified_pg_catalog_table_passes(validator: SchemaValidator) -> None:
    sql = "SELECT pid, query FROM pg_stat_activity LIMIT 10"
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert result.passed, result.errors


@pytest.mark.asyncio
async def test_mixed_case_column_is_case_insensitive(validator: SchemaValidator) -> None:
    # Quoted identifiers are introspected verbatim; the check must not be case-sensitive.
    schema = {"tables": {"orders": {"columns": {"id": {}, "CustomerId": {}}}}}
    result = await validator.validate('SELECT o."CustomerId" FROM orders o', schema)
    assert result.passed, result.errors


@pytest.mark.asyncio
async def test_mixed_case_table_is_case_insensitive(validator: SchemaValidator) -> None:
    schema = {"tables": {"Orders": {"columns": {"id": {}}}}}
    result = await validator.validate("SELECT id FROM orders", schema)
    assert result.passed, result.errors


@pytest.mark.asyncio
async def test_valid_join_passes(validator: SchemaValidator) -> None:
    sql = (
        "SELECT c.name, COUNT(o.id) AS cnt "
        "FROM customers c JOIN orders o ON o.customer_id = c.id "
        "GROUP BY c.name LIMIT 10"
    )
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert result.passed, result.errors
