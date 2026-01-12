import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.history import QueryHistory
from app.schemas.history import HistoryItem


class HistoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: QueryHistory) -> None:
        self._session.add(record)
        await self._session.commit()

    async def get_by_session(
        self, workspace_id: uuid.UUID, session_id: str, limit: int = 50
    ) -> list[HistoryItem]:
        stmt = (
            select(QueryHistory)
            .where(
                QueryHistory.workspace_id == workspace_id,
                QueryHistory.session_id == session_id,
            )
            .order_by(QueryHistory.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_to_item(row) for row in result.scalars().all()]

    async def list_recent(
        self,
        workspace_id: uuid.UUID,
        connection_id: str | None = None,
        limit: int = 50,
    ) -> list[HistoryItem]:
        """Recent runs for the workspace, optionally scoped to one connection."""
        stmt = select(QueryHistory).where(QueryHistory.workspace_id == workspace_id)
        if connection_id:
            try:
                conn_uuid = uuid.UUID(connection_id)
            except ValueError:
                return []
            stmt = stmt.where(QueryHistory.connection_id == conn_uuid)
        stmt = stmt.order_by(QueryHistory.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [_to_item(row) for row in result.scalars().all()]

    async def delete_item(self, workspace_id: uuid.UUID, history_id: str) -> bool:
        """Delete one history row (workspace-scoped). Returns False if not found."""
        try:
            hid = uuid.UUID(history_id)
        except ValueError:
            return False
        record = await self._session.get(QueryHistory, hid)
        if record is None or record.workspace_id != workspace_id:
            return False
        await self._session.delete(record)
        await self._session.commit()
        return True

    async def clear(self, workspace_id: uuid.UUID, connection_id: str | None = None) -> int:
        """Delete all history for the workspace, optionally scoped to a connection."""
        stmt = delete(QueryHistory).where(QueryHistory.workspace_id == workspace_id)
        if connection_id:
            try:
                conn_uuid = uuid.UUID(connection_id)
            except ValueError:
                return 0
            stmt = stmt.where(QueryHistory.connection_id == conn_uuid)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return getattr(result, "rowcount", 0) or 0


def _to_item(row: QueryHistory) -> HistoryItem:
    return HistoryItem(
        id=str(row.id),
        session_id=row.session_id,
        request_id=row.request_id,
        question=row.question,
        final_sql=row.final_sql or "",
        answer=row.answer,
        row_count=row.row_count,
        retry_count=row.retry_count,
        execution_time_ms=row.execution_time_ms,
        created_at=row.created_at,
    )
