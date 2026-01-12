"""bump_fk_weights arq task: nudge FK-edge weights and usage stats for queried tables."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlglot
import sqlglot.expressions as exp
import structlog
from sqlalchemy import select, update

from app.database.engine import get_rw_session_factory
from app.models.schema_index import ConnectionFkEdge, ConnectionTable

log = structlog.get_logger(__name__)

_WEIGHT_DELTA = 0.1


def _referenced_tables(sql: str) -> set[str]:
    try:
        tree = sqlglot.parse_one(sql, dialect="postgres")
    except Exception:
        return set()
    return {t.name.lower() for t in tree.walk() if isinstance(t, exp.Table) and t.name}


async def bump_fk_weights(ctx: dict, *, connection_id: str, sql: str) -> dict:
    names = _referenced_tables(sql)
    if len(names) < 1:
        return {"updated_edges": 0}

    cid = uuid.UUID(connection_id)
    async with get_rw_session_factory()() as db:
        rows = (
            await db.execute(
                select(ConnectionTable.id, ConnectionTable.name).where(
                    ConnectionTable.connection_id == cid
                )
            )
        ).all()
        id_by_name = {name.lower(): tid for tid, name in rows}
        used_ids = {id_by_name[n] for n in names if n in id_by_name}
        if not used_ids:
            return {"updated_edges": 0}

        now = datetime.now(UTC)
        await db.execute(
            update(ConnectionTable)
            .where(ConnectionTable.id.in_(used_ids))
            .values(last_used_at=now, query_count=ConnectionTable.query_count + 1)
        )

        # Only bump edges with both endpoints in the query, which implies a join path.
        edges = (
            await db.scalars(
                select(ConnectionFkEdge).where(
                    ConnectionFkEdge.from_table_id.in_(used_ids),
                    ConnectionFkEdge.to_table_id.in_(used_ids),
                )
            )
        ).all()
        for edge in edges:
            edge.weight = (edge.weight or 1.0) + _WEIGHT_DELTA

        await db.commit()
        log.info("fk_weights.bumped", connection_id=connection_id, edges=len(edges))
        return {"updated_edges": len(edges)}
