from collections.abc import AsyncIterator

from openai import NOT_GIVEN, AsyncOpenAI

from app.llm.base import LLMResponse, Message


class OpenAIProvider:
    """OpenAI provider (BYOK), forcing JSON output via response_format when json_mode is set."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 2048) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def generate(
        self,
        system: str,
        messages: list[Message],
        temperature: float = 0.1,
        json_mode: bool = True,
    ) -> LLMResponse:
        openai_messages = [{"role": "system", "content": system}]
        openai_messages += [{"role": m.role, "content": m.content} for m in messages]

        # json_object mode requires the word "json" in the prompt, so use it only for structured nodes.
        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"} if json_mode else NOT_GIVEN,  # type: ignore[arg-type]
            messages=openai_messages,  # type: ignore[arg-type]
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            model=response.model,
        )

    async def stream(
        self,
        system: str,
        messages: list[Message],
        temperature: float = 0.1,
    ) -> AsyncIterator[str]:
        openai_messages = [{"role": "system", "content": system}]
        openai_messages += [{"role": m.role, "content": m.content} for m in messages]

        stream = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=temperature,
            messages=openai_messages,  # type: ignore[arg-type]
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
