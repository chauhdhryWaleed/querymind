"""Per-query thumbs-up/down with optional reason, wired to query_history.request_id."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models._columns import created_at, pk


class QueryFeedback(Base):
    __tablename__ = "query_feedback"

    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[str] = mapped_column(index=True)
    session_id: Mapped[str] = mapped_column(index=True)
    rating: Mapped[str]  # "up" | "down"
    reason: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = created_at()
