"""index_connection_schema arq task: introspect a connection and (re)build its schema index."""

from __future__ import annotations

import uuid

from app.database.engine import get_rw_session_factory
from app.drivers import ConnectionCredentials
from app.ml.embedder import get_embedder
from app.services.schema_index_service import SchemaIndexService


async def index_connection_schema(ctx: dict, *, connection_id: str, creds: dict) -> dict:
    credentials = ConnectionCredentials(**creds)
    embedder = get_embedder()
    async with get_rw_session_factory()() as db:
        service = SchemaIndexService(db, embedder)
        table_count = await service.index(uuid.UUID(connection_id), credentials)
    return {"connection_id": connection_id, "tables_indexed": table_count}
