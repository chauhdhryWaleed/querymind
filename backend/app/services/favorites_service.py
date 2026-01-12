from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite import SavedQuery
from app.schemas.favorites import FavoriteItem, SaveFavoriteRequest


class FavoritesService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, payload: SaveFavoriteRequest
    ) -> FavoriteItem:
        record = SavedQuery(
            workspace_id=workspace_id,
            user_id=user_id,
            name=payload.name.strip(),
            question=payload.question.strip(),
            sql=payload.sql.strip(),
            tags=payload.tags.strip() if payload.tags else None,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return _to_item(record)

    async def list(self, workspace_id: uuid.UUID, limit: int = 100) -> list[FavoriteItem]:
        stmt = (
            select(SavedQuery)
            .where(SavedQuery.workspace_id == workspace_id)
            .order_by(SavedQuery.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows: Sequence[SavedQuery] = result.scalars().all()
        return [_to_item(r) for r in rows]

    async def delete(self, workspace_id: uuid.UUID, favorite_id: str) -> bool:
        try:
            uid = uuid.UUID(favorite_id)
        except ValueError:
            return False
        record = await self._session.get(SavedQuery, uid)
        if not record or record.workspace_id != workspace_id:
            return False
        await self._session.delete(record)
        await self._session.commit()
        return True


def _to_item(record: SavedQuery) -> FavoriteItem:
    return FavoriteItem(
        id=str(record.id),
        name=record.name,
        question=record.question,
        sql=record.sql,
        tags=record.tags,
        created_at=record.created_at,
    )
