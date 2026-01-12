import sqlglot
from sqlalchemy.ext.asyncio import AsyncSession

from app.validators.base import BaseValidator, ValidationResult


class SyntaxValidator(BaseValidator):
    """Validates SQL syntax using sqlglot's postgres dialect parser."""

    @property
    def stage_name(self) -> str:
        return "syntax"

    async def validate(
        self,
        sql: str,
        schema: dict,
        session: AsyncSession | None = None,
    ) -> ValidationResult:
        if not sql or not sql.strip():
            return self._fail("SQL query is empty.")

        try:
            sqlglot.transpile(
                sql,
                read="postgres",
                write="postgres",
                error_level=sqlglot.ErrorLevel.RAISE,
            )
        except sqlglot.errors.ParseError as exc:
            messages = "; ".join(str(e) for e in exc.errors) if exc.errors else str(exc)
            return self._fail(f"SQL syntax error: {messages}")

        return self._pass()
