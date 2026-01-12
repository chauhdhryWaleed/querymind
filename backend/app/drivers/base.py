"""Driver Protocol + shared credential/result types + a dialect factory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ConnectionCredentials:
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str | None = None  # disable | prefer | require | verify-ca | verify-full


@dataclass(frozen=True)
class ConnectionTestResult:
    ok: bool
    message: str
    server_version: str | None = None
    latency_ms: float | None = None


@dataclass(frozen=True)
class IntrospectedColumn:
    name: str
    data_type: str
    is_nullable: bool
    is_pk: bool
    is_fk: bool
    default_expr: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class IntrospectedTable:
    schema_name: str
    name: str
    kind: str  # table | view | mview
    row_count: int | None
    description: str | None
    columns: list[IntrospectedColumn]


@dataclass(frozen=True)
class IntrospectedFk:
    from_schema: str
    from_table: str
    from_column: str
    to_schema: str
    to_table: str
    to_column: str


@dataclass(frozen=True)
class IntrospectedSchema:
    tables: list[IntrospectedTable]
    fks: list[IntrospectedFk]


@runtime_checkable
class DBDriver(Protocol):
    """A driver for one SQL dialect against a user-supplied database."""

    dialect: str

    async def test(
        self, creds: ConnectionCredentials, *, timeout: float = ...
    ) -> ConnectionTestResult:
        """Open a connection, run a trivial probe, and report reachability."""
        ...

    async def introspect(
        self, creds: ConnectionCredentials, *, timeout: float = ...
    ) -> IntrospectedSchema:
        """Read-only introspection of tables, columns, and FK edges."""
        ...


def get_driver(dialect: str) -> DBDriver:
    """Return the driver for a dialect. Postgres in Phase 1; MySQL in Phase 2."""
    if dialect == "postgres":
        from app.drivers.postgres import PostgresDriver

        return PostgresDriver()
    raise ValueError(f"Unsupported dialect: {dialect!r}")
