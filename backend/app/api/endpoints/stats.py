from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_api_key
from app.database.session import get_rw_session
from app.schemas.stats import StatsResponse
from app.services.stats_service import StatsService

router = APIRouter(tags=["stats"], dependencies=[Depends(require_api_key)])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    session: Annotated[AsyncSession, Depends(get_rw_session)],
    window_days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> StatsResponse:
    return await StatsService(session).summary(window_days=window_days)
