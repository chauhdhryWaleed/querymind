import sqlglot
import sqlglot.expressions as exp
from sqlalchemy.ext.asyncio import AsyncSession

from app.validators.base import BaseValidator, ValidationResult

_FORBIDDEN_NODE_TYPES = (
    exp.Drop,
    exp.Delete,
    exp.Update,
    exp.Insert,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,  # added v0.6
    exp.Merge,
    exp.Command,  # catches arbitrary DDL that sqlglot doesn't model specifically
)


class SafetyValidator(BaseValidator):
    """Blocks any statement that would mutate schema or data."""

    @property
    def stage_name(self) -> str:
        return "safety"

    async def validate(
        self,
        sql: str,
        schema: dict,
        session: AsyncSession | None = None,
    ) -> ValidationResult:
        try:
            statements = sqlglot.parse(sql, dialect="postgres")
        except Exception:
            # Defer to SyntaxValidator for actual parse errors.
            return self._pass()

        violations: list[str] = []
        for statement in statements:
            if statement is None:
                continue
            for node in statement.walk():
                if isinstance(node, _FORBIDDEN_NODE_TYPES):
                    violations.append(f"Forbidden operation: {type(node).__name__} is not allowed.")

        if violations:
            return self._fail(*violations)
        return self._pass()
