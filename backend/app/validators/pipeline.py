from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.validators.base import BaseValidator, ValidationResult
from app.validators.complexity import ComplexityValidator
from app.validators.explain import ExplainValidator
from app.validators.safety import SafetyValidator
from app.validators.schema_check import SchemaValidator
from app.validators.syntax import SyntaxValidator


class ValidationPipeline:
    """Runs validators in order (deliberately cheapest to most expensive), failing fast on the first error."""

    def __init__(self, validators: list[BaseValidator]) -> None:
        self._validators = validators

    @classmethod
    def default(cls, settings: Settings) -> "ValidationPipeline":
        return cls(
            [
                SafetyValidator(),
                SyntaxValidator(),
                SchemaValidator(),
                ComplexityValidator(),
                ExplainValidator(),
            ]
        )

    async def run(
        self,
        sql: str,
        schema: dict,
        session: AsyncSession | None = None,
    ) -> ValidationResult:
        for validator in self._validators:
            result = await validator.validate(sql, schema, session)
            if not result.passed:
                return result
        return ValidationResult(passed=True, errors=[], stage="pipeline")
