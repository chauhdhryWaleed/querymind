from collections.abc import AsyncIterator

import anthropic

from app.llm.base import LLMResponse, Message


class AnthropicProvider:
    """Anthropic Claude provider (BYOK), caching the system prompt to cut repeated-call cost."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 2048) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def generate(
        self,
        system: str,
        messages: list[Message],
        temperature: float = 0.1,
        json_mode: bool = True,
    ) -> LLMResponse:
        # Claude has no json_object switch, so json_mode is accepted only for interface parity.
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=temperature,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        return LLMResponse(
            content=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
        )

    async def stream(
        self,
        system: str,
        messages: list[Message],
        temperature: float = 0.1,
    ) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=temperature,
            system=[{"type": "text", "text": system}],
            messages=[{"role": m.role, "content": m.content} for m in messages],
        ) as stream:
            async for text in stream.text_stream:
                yield text
