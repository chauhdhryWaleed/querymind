"""Request/response models for BYOK LLM key management; the API key is write-only, responses include only a masked hint."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Provider = Literal["anthropic", "openai", "gemini"]


class LlmKeyCreate(BaseModel):
    provider: Provider
    label: str | None = Field(default=None, max_length=200)
    api_key: str = Field(min_length=1, max_length=1024)
    model_override: str | None = Field(default=None, max_length=200)
    is_default: bool = False


class LlmKeyUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    api_key: str | None = Field(default=None, min_length=1, max_length=1024)
    model_override: str | None = Field(default=None, max_length=200)
    is_default: bool | None = None


class LlmKeyOut(BaseModel):
    id: uuid.UUID
    provider: str
    label: str | None
    model_override: str | None
    is_default: bool
    key_hint: str  # e.g. "…a1b2"
    created_at: datetime
