"""SchemaIndexService: introspect a user DB and persist the schema index as a full replace."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import UTC

import structlog
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.drivers import ConnectionCredentials, IntrospectedSchema, get_driver
from app.ml.embedder import EmbedderProtocol
from app.models.connection import Connection
from app.models.schema_index import ConnectionColumn, ConnectionFkEdge, ConnectionTable

log = structlog.get_logger(__name__)


def build_table_signature(table, fks_from: list, fks_to: list) -> str:
    """Render the embedding signature for one table; fks_from are outgoing refs, fks_to incoming."""
    col_names = ", ".join(c.name for c in table.columns)
    lines = [
        f"[{table.kind}: {table.name}] (schema {table.schema_name})",
        f"purpose: {table.description or ''}",
        f"columns: {col_names}",
    ]
    if fks_from:
        refs = ", ".join(f"{f.from_column} -> {f.to_table}.{f.to_column}" for f in fks_from)
        lines.append(f"references: {refs}")
    if fks_to:
        refd = ", ".join(f"{f.from_table}.{f.from_column}" for f in fks_to)
        lines.append(f"referenced by: {refd}")
    if table.row_count is not None:
        lines.append(f"row_count: ~{table.row_count}")
    return "\n".join(lines)


def compute_schema_hash(schema: IntrospectedSchema) -> str:
    """Cheap structural fingerprint for drift detection (counts per table)."""
    parts = sorted(f"{t.schema_name}.{t.name}:{len(t.columns)}" for t in schema.tables)
    parts.append(f"fks:{len(schema.fks)}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


class SchemaIndexService:
    def __init__(self, db: AsyncSession, embedder: EmbedderProtocol) -> None:
        self._db = db
        self._embedder = embedder

    async def index(self, connection_id: uuid.UUID, creds: ConnectionCredentials) -> int:
        """Introspect and (re)build the index for one connection, updating index_status."""
        conn = await self._db.get(Connection, connection_id)
        if conn is None:
            raise ValueError(f"Connection {connection_id} not found")

        conn.index_status = "indexing"
        conn.index_error = None
        await self._db.commit()

        try:
            driver = get_driver(conn.dialect)
            schema = await driver.introspect(creds)
            count = await self._persist(conn, schema)
            conn.index_status = "ready"
            conn.schema_hash = compute_schema_hash(schema)
            from datetime import datetime

            conn.last_introspected_at = datetime.now(UTC)
            await self._db.commit()
            log.info("schema.indexed", connection_id=str(connection_id), tables=count)
            return count
        except Exception as exc:  # noqa: BLE001 - record + re-raise for the worker
            await self._db.rollback()
            conn = await self._db.get(Connection, connection_id)
            if conn is not None:
                conn.index_status = "failed"
                conn.index_error = f"{type(exc).__name__}: {exc}"[:500]
                await self._db.commit()
            log.error("schema.index_failed", connection_id=str(connection_id), error=str(exc))
            raise

    async def _persist(self, conn: Connection, schema: IntrospectedSchema) -> int:
        # Full replace: drop old rows (columns + edges cascade via FK ondelete).
        await self._db.execute(
            delete(ConnectionTable).where(ConnectionTable.connection_id == conn.id)
        )

        # Group FK edges by table for signature building.
        fks_from: dict[tuple[str, str], list] = {}
        fks_to: dict[tuple[str, str], list] = {}
        for fk in schema.fks:
            fks_from.setdefault((fk.from_schema, fk.from_table), []).append(fk)
            fks_to.setdefault((fk.to_schema, fk.to_table), []).append(fk)

        signatures = [
            build_table_signature(
                t,
                fks_from.get((t.schema_name, t.name), []),
                fks_to.get((t.schema_name, t.name), []),
            )
            for t in schema.tables
        ]
        # Embedding is CPU-bound and synchronous; run off the event loop.
        embeddings = await asyncio.to_thread(self._embedder.encode_documents, signatures)

        id_by_ident: dict[tuple[str, str], uuid.UUID] = {}
        for table, signature, embedding in zip(schema.tables, signatures, embeddings, strict=True):
            row = ConnectionTable(
                connection_id=conn.id,
                schema_name=table.schema_name,
                name=table.name,
                kind=table.kind,
                row_count=table.row_count,
                description=table.description,
                embedding=embedding,
                signature_hash=hashlib.sha256(signature.encode()).hexdigest(),
            )
            self._db.add(row)
            await self._db.flush()
            id_by_ident[(table.schema_name, table.name)] = row.id
            for col in table.columns:
                self._db.add(
                    ConnectionColumn(
                        table_id=row.id,
                        name=col.name,
                        data_type=col.data_type,
                        is_nullable=col.is_nullable,
                        is_pk=col.is_pk,
                        is_fk=col.is_fk,
                        default_expr=col.default_expr,
                        description=col.description,
                        embedding=None,  # column vectors are Phase 2
                    )
                )

        # FK edges (only where both endpoints were indexed).
        for fk in schema.fks:
            src = id_by_ident.get((fk.from_schema, fk.from_table))
            dst = id_by_ident.get((fk.to_schema, fk.to_table))
            if src is None or dst is None:
                continue
            self._db.add(
                ConnectionFkEdge(
                    from_table_id=src,
                    from_column=fk.from_column,
                    to_table_id=dst,
                    to_column=fk.to_column,
                )
            )
        await self._db.flush()
        return len(schema.tables)
