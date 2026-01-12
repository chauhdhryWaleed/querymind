"""User-supplied target databases. All credential fields are AES-GCM ciphertext."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models._columns import created_at, pk


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str]
    dialect: Mapped[str]  # "postgres" | "mysql"

    # Per-connection DEK, itself wrapped with the session ENC_KEY (AES-GCM).
    wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary)

    # Credential fields, each AES-GCM encrypted under the DEK.
    host_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    port_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    database_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    username_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    password_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    ssl_mode: Mapped[str | None] = mapped_column(nullable=True)
    read_only: Mapped[bool] = mapped_column(default=True, server_default="true")

    schema_hash: Mapped[str | None] = mapped_column(nullable=True)
    last_introspected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    index_status: Mapped[str] = mapped_column(
        default="pending", server_default="pending"
    )  # "pending" | "indexing" | "ready" | "failed"
    index_error: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = created_at()
