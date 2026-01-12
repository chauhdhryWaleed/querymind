"""Gemini provider (BYOK); per-Client api_key avoids clashes but is untested against a live key."""

from __future__ import annotations

from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from app.llm.base import LLMResponse, Message


class GeminiProvider:
    def __init__(self, api_key: str, model: str, max_tokens: int = 2048) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def _config(
        self, system: str, temperature: float, json: bool = True
    ) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=self._max_tokens,
            response_mime_type="application/json" if json else "text/plain",
        )

    @staticmethod
    def _contents(messages: list[Message]) -> str:
        # The agent sends a single user turn; join defensively if more arrive.
        return "\n".join(m.content for m in messages if m.role == "user")

    async def generate(
        self,
        system: str,
        messages: list[Message],
        temperature: float = 0.1,
        json_mode: bool = True,
    ) -> LLMResponse:
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=self._contents(messages),
            config=self._config(system, temperature, json=json_mode),
        )
        usage = response.usage_metadata
        return LLMResponse(
            content=response.text or "",
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            model=self._model,
        )

    async def stream(
        self, system: str, messages: list[Message], temperature: float = 0.1
    ) -> AsyncIterator[str]:
        stream = await self._client.aio.models.generate_content_stream(
            model=self._model,
            contents=self._contents(messages),
            config=self._config(system, temperature, json=False),
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
