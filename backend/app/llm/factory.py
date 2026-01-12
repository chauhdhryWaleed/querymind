"""Per-request BYOK LLM provider construction."""

from __future__ import annotations

from app.config.settings import Settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.openai_provider import OpenAIProvider


def default_model(provider: str, settings: Settings) -> str:
    return {
        "anthropic": settings.ANTHROPIC_MODEL,
        "openai": settings.OPENAI_MODEL,
        "gemini": settings.GEMINI_MODEL,
    }[provider]


def build_llm_provider(
    provider: str, api_key: str, model: str, max_tokens: int = 2048
) -> LLMProvider:
    """Construct a provider from an explicit (BYOK) key + model."""
    if provider == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model, max_tokens=max_tokens)
    if provider == "openai":
        return OpenAIProvider(api_key=api_key, model=model, max_tokens=max_tokens)
    if provider == "gemini":
        return GeminiProvider(api_key=api_key, model=model, max_tokens=max_tokens)
    raise ValueError(f"Unknown LLM provider: {provider!r}")
