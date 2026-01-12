from abc import ABC, abstractmethod

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


class ValidationResult(BaseModel):
    passed: bool
    errors: list[str]
    stage: str


class BaseValidator(ABC):
    @property
    @abstractmethod
    def stage_name(self) -> str: ...

    @abstractmethod
    async def validate(
        self,
        sql: str,
        schema: dict,
        session: AsyncSession | None = None,
    ) -> ValidationResult: ...

    def _fail(self, *errors: str) -> ValidationResult:
        return ValidationResult(passed=False, errors=list(errors), stage=self.stage_name)

    def _pass(self) -> ValidationResult:
        return ValidationResult(passed=True, errors=[], stage=self.stage_name)
