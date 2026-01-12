import pytest

from app.validators.complexity import ComplexityValidator


@pytest.fixture
def validator() -> ComplexityValidator:
    return ComplexityValidator()


@pytest.mark.asyncio
async def test_large_limit_is_allowed(validator: ComplexityValidator) -> None:
    # The executor caps rows; the validator no longer rejects an oversized LIMIT.
    result = await validator.validate("SELECT id FROM orders LIMIT 100000", {})
    assert result.passed, result.errors


@pytest.mark.asyncio
async def test_unbounded_cross_join_fails(validator: ComplexityValidator) -> None:
    result = await validator.validate("SELECT * FROM customers CROSS JOIN orders", {})
    assert not result.passed
    assert any("CROSS JOIN" in e for e in result.errors)


@pytest.mark.asyncio
async def test_bounded_cross_join_passes(validator: ComplexityValidator) -> None:
    sql = "SELECT * FROM customers c CROSS JOIN orders o WHERE o.customer_id = c.id"
    result = await validator.validate(sql, {})
    assert result.passed, result.errors


@pytest.mark.asyncio
async def test_plain_query_passes(validator: ComplexityValidator) -> None:
    result = await validator.validate("SELECT id FROM orders LIMIT 10", {})
    assert result.passed, result.errors
