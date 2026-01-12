from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import QueryFeedback
from app.schemas.feedback import FeedbackRequest, FeedbackResponse


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str,
        payload: FeedbackRequest,
    ) -> FeedbackResponse:
        record = QueryFeedback(
            workspace_id=workspace_id,
            user_id=user_id,
            request_id=request_id,
            session_id=payload.session_id or "",
            rating=payload.rating,
            reason=(payload.reason or None),
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return FeedbackResponse(
            id=str(record.id), request_id=record.request_id, rating=record.rating
        )
