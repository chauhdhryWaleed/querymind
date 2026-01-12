from collections.abc import AsyncIterator
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class LLMResponse(BaseModel):
    content: str
    input_tokens: int
    output_tokens: int
    model: str


@runtime_checkable
class LLMProvider(Protocol):
    async def generate(
        self,
        system: str,
        messages: list[Message],
        temperature: float = 0.1,
        json_mode: bool = True,
    ) -> LLMResponse: ...

    def stream(
        self,
        system: str,
        messages: list[Message],
        temperature: float = 0.1,
    ) -> AsyncIterator[str]: ...
