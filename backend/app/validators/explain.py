from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.validators.base import BaseValidator, ValidationResult


class ExplainValidator(BaseValidator):
    """Runs EXPLAIN (FORMAT JSON) to catch runtime semantic errors without executing the query."""

    @property
    def stage_name(self) -> str:
        return "explain"

    async def validate(
        self,
        sql: str,
        schema: dict,
        session: AsyncSession | None = None,
    ) -> ValidationResult:
        if session is None:
            # No DB session available (e.g., unit tests without a real DB).
            return self._pass()

        try:
            await session.execute(text(f"EXPLAIN (FORMAT JSON) {sql}"))
            return self._pass()
        except Exception as exc:
            # Strip SQLAlchemy wrapper noise to surface the real PG error.
            error_msg = str(exc)
            pg_error = error_msg.split("ERROR:")[-1].strip() if "ERROR:" in error_msg else error_msg
            return self._fail(f"Query plan error: {pg_error}")
