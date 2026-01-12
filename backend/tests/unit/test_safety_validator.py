import pytest

from app.validators.safety import SafetyValidator
from tests.fixtures.sample_queries import INVALID_QUERIES_SAFETY, VALID_QUERIES
from tests.fixtures.sample_schema import SAMPLE_SCHEMA


@pytest.fixture
def validator() -> SafetyValidator:
    return SafetyValidator()


@pytest.mark.asyncio
@pytest.mark.parametrize("sql", VALID_QUERIES)
async def test_valid_queries_pass(validator: SafetyValidator, sql: str) -> None:
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert result.passed, f"Expected PASS for: {sql}\nErrors: {result.errors}"


@pytest.mark.asyncio
@pytest.mark.parametrize("sql", INVALID_QUERIES_SAFETY)
async def test_dangerous_queries_blocked(validator: SafetyValidator, sql: str) -> None:
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert not result.passed, f"Expected FAIL for: {sql}"
    assert result.errors
