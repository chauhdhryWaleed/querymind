"""Per-user query history. Tenant FKs are nullable until M4 wires the query path to auth."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models._columns import created_at, pk


class QueryHistory(Base):
    __tablename__ = "query_history"

    id: Mapped[uuid.UUID] = pk()

    # Tenant scoping (NOT NULL since M4; the query path is auth-wired).
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("connections.id", ondelete="SET NULL"), nullable=True
    )
    llm_key_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("llm_keys.id", ondelete="SET NULL"), nullable=True
    )

    session_id: Mapped[str] = mapped_column(index=True)
    request_id: Mapped[str] = mapped_column(index=True)
    question: Mapped[str]
    generated_sql: Mapped[str | None] = mapped_column(nullable=True)
    final_sql: Mapped[str | None] = mapped_column(nullable=True)
    # Stored answer so History can show the result without re-running the query.
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_tables: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    execution_time_ms: Mapped[float] = mapped_column(default=0.0)
    row_count: Mapped[int] = mapped_column(default=0)
    retry_count: Mapped[int] = mapped_column(default=0)
    llm_provider: Mapped[str | None] = mapped_column(nullable=True)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = created_at()
