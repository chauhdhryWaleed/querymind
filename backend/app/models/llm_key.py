"""BYOK LLM API keys. The key itself is AES-GCM ciphertext under a wrapped DEK."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models._columns import created_at, pk


class LlmKey(Base):
    __tablename__ = "llm_keys"

    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str]  # "anthropic" | "openai" | "gemini"
    label: Mapped[str | None] = mapped_column(nullable=True)

    wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary)
    api_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary)

    model_override: Mapped[str | None] = mapped_column(nullable=True)
    is_default: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_at: Mapped[datetime] = created_at()
