"""ConnectionService: encrypted CRUD for user database connections (per-connection DEK)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.drivers import ConnectionCredentials, ConnectionTestResult, get_driver
from app.models.connection import Connection
from app.models.schema_index import ConnectionColumn, ConnectionFkEdge, ConnectionTable
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionOut,
    ConnectionUpdate,
    FkEdgeOut,
    IndexedColumnOut,
    IndexedSchemaOut,
    IndexedTableOut,
)
from app.security import crypto
from app.services.audit_service import AuditService


class ConnectionService:
    def __init__(self, db: AsyncSession, enc_key: bytes, audit: AuditService) -> None:
        self._db = db
        self._enc_key = enc_key
        self._audit = audit

    def _dek(self, conn: Connection) -> bytes:
        return crypto.unwrap_dek(conn.wrapped_dek, self._enc_key)

    def _decrypted(self, conn: Connection) -> ConnectionCredentials:
        dek = self._dek(conn)
        return ConnectionCredentials(
            host=crypto.decrypt_str(conn.host_encrypted, dek),
            port=int(crypto.decrypt_str(conn.port_encrypted, dek)),
            database=crypto.decrypt_str(conn.database_encrypted, dek),
            username=crypto.decrypt_str(conn.username_encrypted, dek),
            password=crypto.decrypt_str(conn.password_encrypted, dek)
            if conn.password_encrypted
            else "",
            ssl_mode=conn.ssl_mode,
        )

    def credentials(self, conn: Connection) -> ConnectionCredentials:
        """Decrypt full credentials (incl. password) for testing/introspection."""
        return self._decrypted(conn)

    def to_out(self, conn: Connection) -> ConnectionOut:
        """Decrypt non-secret fields for display. Password is never returned."""
        creds = self._decrypted(conn)
        return ConnectionOut(
            id=conn.id,
            name=conn.name,
            dialect=conn.dialect,
            host=creds.host,
            port=creds.port,
            database=creds.database,
            username=creds.username,
            ssl_mode=conn.ssl_mode,
            read_only=conn.read_only,
            index_status=conn.index_status,
            index_error=conn.index_error,
            last_introspected_at=conn.last_introspected_at,
            created_at=conn.created_at,
        )

    async def create(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, payload: ConnectionCreate
    ) -> Connection:
        dek = crypto.generate_dek()
        conn = Connection(
            workspace_id=workspace_id,
            name=payload.name,
            dialect=payload.dialect,
            wrapped_dek=crypto.wrap_dek(dek, self._enc_key),
            host_encrypted=crypto.encrypt_str(payload.host, dek),
            port_encrypted=crypto.encrypt_str(str(payload.port), dek),
            database_encrypted=crypto.encrypt_str(payload.database, dek),
            username_encrypted=crypto.encrypt_str(payload.username, dek),
            password_encrypted=crypto.encrypt_str(payload.password, dek),
            ssl_mode=payload.ssl_mode,
            read_only=payload.read_only,
            index_status="pending",
        )
        self._db.add(conn)
        await self._db.flush()
        await self._audit.record(
            "connection.create",
            user_id=user_id,
            workspace_id=workspace_id,
            payload={"connection_id": str(conn.id), "name": conn.name},
        )
        await self._db.commit()
        await self._db.refresh(conn)
        return conn

    async def list(self, workspace_id: uuid.UUID) -> list[Connection]:
        rows = await self._db.scalars(
            select(Connection)
            .where(Connection.workspace_id == workspace_id)
            .order_by(Connection.created_at.desc())
        )
        return list(rows.all())

    async def get(self, workspace_id: uuid.UUID, conn_id: uuid.UUID) -> Connection | None:
        """Scoped fetch: returns None if the connection isn't in this workspace."""
        conn = await self._db.get(Connection, conn_id)
        if conn is None or conn.workspace_id != workspace_id:
            return None
        return conn

    async def update(
        self, conn: Connection, user_id: uuid.UUID, payload: ConnectionUpdate
    ) -> Connection:
        dek = self._dek(conn)
        if payload.name is not None:
            conn.name = payload.name
        if payload.host is not None:
            conn.host_encrypted = crypto.encrypt_str(payload.host, dek)
        if payload.port is not None:
            conn.port_encrypted = crypto.encrypt_str(str(payload.port), dek)
        if payload.database is not None:
            conn.database_encrypted = crypto.encrypt_str(payload.database, dek)
        if payload.username is not None:
            conn.username_encrypted = crypto.encrypt_str(payload.username, dek)
        if payload.password is not None:  # omitted ⇒ keep existing password
            conn.password_encrypted = crypto.encrypt_str(payload.password, dek)
        if payload.ssl_mode is not None:
            conn.ssl_mode = payload.ssl_mode
        if payload.read_only is not None:
            conn.read_only = payload.read_only
        await self._audit.record(
            "connection.update",
            user_id=user_id,
            workspace_id=conn.workspace_id,
            payload={"connection_id": str(conn.id)},
        )
        await self._db.commit()
        await self._db.refresh(conn)
        return conn

    async def delete(self, conn: Connection, user_id: uuid.UUID) -> None:
        await self._audit.record(
            "connection.delete",
            user_id=user_id,
            workspace_id=conn.workspace_id,
            payload={"connection_id": str(conn.id), "name": conn.name},
        )
        await self._db.delete(conn)
        await self._db.commit()

    async def test(self, conn: Connection) -> ConnectionTestResult:
        creds = self._decrypted(conn)
        driver = get_driver(conn.dialect)
        return await driver.test(creds)

    async def get_indexed_schema(self, conn: Connection) -> IndexedSchemaOut:
        """Read the stored schema index without hitting the live database."""
        tables = list(
            (
                await self._db.scalars(
                    select(ConnectionTable)
                    .where(ConnectionTable.connection_id == conn.id)
                    .order_by(ConnectionTable.schema_name, ConnectionTable.name)
                )
            ).all()
        )
        table_ids = [t.id for t in tables]
        name_by_id = {t.id: t.name for t in tables}

        cols_by_table: dict[uuid.UUID, list[IndexedColumnOut]] = {}
        if table_ids:
            for c in (
                await self._db.scalars(
                    select(ConnectionColumn).where(ConnectionColumn.table_id.in_(table_ids))
                )
            ).all():
                cols_by_table.setdefault(c.table_id, []).append(
                    IndexedColumnOut(
                        name=c.name,
                        data_type=c.data_type,
                        is_nullable=c.is_nullable,
                        is_pk=c.is_pk,
                        is_fk=c.is_fk,
                    )
                )

        fks: list[FkEdgeOut] = []
        if table_ids:
            for e in (
                await self._db.scalars(
                    select(ConnectionFkEdge).where(ConnectionFkEdge.from_table_id.in_(table_ids))
                )
            ).all():
                fks.append(
                    FkEdgeOut(
                        from_table=name_by_id.get(e.from_table_id, "?"),
                        from_column=e.from_column,
                        to_table=name_by_id.get(e.to_table_id, "?"),
                        to_column=e.to_column,
                    )
                )

        return IndexedSchemaOut(
            index_status=conn.index_status,
            table_count=len(tables),
            tables=[
                IndexedTableOut(
                    id=t.id,
                    schema_name=t.schema_name,
                    name=t.name,
                    kind=t.kind,
                    row_count=t.row_count,
                    description=t.description,
                    columns=cols_by_table.get(t.id, []),
                )
                for t in tables
            ],
            fks=fks,
        )
