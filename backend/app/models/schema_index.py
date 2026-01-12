"""The indexed schema slice powering retrieval: per-table records, columns, and the FK graph (384-dim embeddings)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models._columns import pk


class ConnectionTable(Base):
    __tablename__ = "connection_tables"
    __table_args__ = (UniqueConstraint("connection_id", "schema_name", "name"),)

    id: Mapped[uuid.UUID] = pk()
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connections.id", ondelete="CASCADE"), index=True
    )
    schema_name: Mapped[str] = mapped_column(default="public", server_default="public")
    name: Mapped[str]
    kind: Mapped[str]  # "table" | "view" | "mview" | "partition"
    row_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    priority: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    signature_hash: Mapped[str]
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    query_count: Mapped[int] = mapped_column(default=0, server_default="0")


class ConnectionColumn(Base):
    __tablename__ = "connection_columns"

    id: Mapped[uuid.UUID] = pk()
    table_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connection_tables.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str]
    data_type: Mapped[str]
    is_nullable: Mapped[bool | None] = mapped_column(nullable=True)
    is_pk: Mapped[bool | None] = mapped_column(nullable=True)
    is_fk: Mapped[bool | None] = mapped_column(nullable=True)
    default_expr: Mapped[str | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)


class ConnectionFkEdge(Base):
    __tablename__ = "connection_fk_edges"

    id: Mapped[uuid.UUID] = pk()
    from_table_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connection_tables.id", ondelete="CASCADE"), index=True
    )
    from_column: Mapped[str]
    to_table_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connection_tables.id", ondelete="CASCADE"), index=True
    )
    to_column: Mapped[str]
    weight: Mapped[float] = mapped_column(Float, default=1.0, server_default="1.0")
