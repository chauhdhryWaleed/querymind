"""Liveness/readiness check exposed at GET /health."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.config.settings import Settings, get_settings
from app.database.engine import get_rw_session_factory

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    db: bool
    redis: bool
    version: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    db_ok = False
    redis_ok = False

    try:
        async with get_rw_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    try:
        await request.app.state.redis.ping()
        redis_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok" if (db_ok and redis_ok) else "degraded",
        db=db_ok,
        redis=redis_ok,
        version=settings.VERSION,
        timestamp=datetime.now(tz=UTC),
    )
