import pytest

from app.validators.syntax import SyntaxValidator
from tests.fixtures.sample_queries import INVALID_QUERIES_SYNTAX, VALID_QUERIES
from tests.fixtures.sample_schema import SAMPLE_SCHEMA


@pytest.fixture
def validator() -> SyntaxValidator:
    return SyntaxValidator()


@pytest.mark.asyncio
@pytest.mark.parametrize("sql", VALID_QUERIES)
async def test_valid_queries_pass(validator: SyntaxValidator, sql: str) -> None:
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert result.passed, f"Expected PASS for: {sql}\nErrors: {result.errors}"


@pytest.mark.asyncio
@pytest.mark.parametrize("sql", INVALID_QUERIES_SYNTAX)
async def test_invalid_syntax_fails(validator: SyntaxValidator, sql: str) -> None:
    result = await validator.validate(sql, SAMPLE_SCHEMA)
    assert not result.passed, f"Expected FAIL for: {sql}"


@pytest.mark.asyncio
async def test_empty_sql_fails(validator: SyntaxValidator) -> None:
    result = await validator.validate("", SAMPLE_SCHEMA)
    assert not result.passed
    assert "empty" in result.errors[0].lower()
