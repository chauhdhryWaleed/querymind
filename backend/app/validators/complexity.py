import sqlglot
import sqlglot.expressions as exp
from sqlalchemy.ext.asyncio import AsyncSession

from app.validators.base import BaseValidator, ValidationResult


class ComplexityValidator(BaseValidator):
    """Rejects an unbounded CROSS JOIN (one with no WHERE filter).

    Row counts are not checked here: the executor caps every query to MAX_ROWS,
    so an oversized LIMIT is capped rather than rejected.
    """

    @property
    def stage_name(self) -> str:
        return "complexity"

    async def validate(
        self,
        sql: str,
        schema: dict,
        session: AsyncSession | None = None,
    ) -> ValidationResult:
        try:
            tree = sqlglot.parse_one(sql, dialect="postgres")
        except Exception:
            return self._pass()

        for node in tree.walk():
            if isinstance(node, exp.Join) and node.kind == "CROSS":
                select = node.parent_select
                if select is None or select.args.get("where") is None:
                    return self._fail(
                        "Unbounded CROSS JOIN: add a WHERE filter to bound the result set."
                    )

        return self._pass()
