"""Request/response models for connection management; passwords are write-only and never returned once saved."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Dialect = Literal["postgres", "mysql"]


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dialect: Dialect = "postgres"
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535, default=5432)
    database: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(default="", max_length=1024)
    ssl_mode: str | None = None
    read_only: bool = True


class ConnectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    database: str | None = Field(default=None, min_length=1, max_length=255)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    # Only re-supply to change it; omit to keep the stored password.
    password: str | None = Field(default=None, max_length=1024)
    ssl_mode: str | None = None
    read_only: bool | None = None


class ConnectionOut(BaseModel):
    id: uuid.UUID
    name: str
    dialect: str
    host: str
    port: int
    database: str
    username: str
    ssl_mode: str | None
    read_only: bool
    index_status: str
    index_error: str | None
    last_introspected_at: datetime | None
    created_at: datetime


class ConnectionTestResponse(BaseModel):
    ok: bool
    message: str
    server_version: str | None = None
    latency_ms: float | None = None


# Indexed schema is read from our own index, not the live DB.


class IndexedColumnOut(BaseModel):
    name: str
    data_type: str
    is_nullable: bool | None
    is_pk: bool | None
    is_fk: bool | None


class IndexedTableOut(BaseModel):
    id: uuid.UUID
    schema_name: str
    name: str
    kind: str
    row_count: int | None
    description: str | None
    columns: list[IndexedColumnOut]


class FkEdgeOut(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class IndexedSchemaOut(BaseModel):
    index_status: str
    table_count: int
    tables: list[IndexedTableOut]
    fks: list[FkEdgeOut]
