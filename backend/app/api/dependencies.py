"""FastAPI dependency providers for query-path collaborators."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis

from app.config.settings import Settings, get_settings
from app.executors.sql_executor import SqlExecutor
from app.memory.conversation import ConversationMemory
from app.validators.pipeline import ValidationPipeline


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_arq(request: Request):
    """arq pool for enqueuing jobs, or None if unavailable (degraded mode)."""
    return getattr(request.app.state, "arq", None)


def get_embedder():
    """Process-wide bge-small embedder (lazy-loaded). Overridable in tests."""
    from app.ml.embedder import get_embedder as _get

    return _get()


def get_executor(settings: Annotated[Settings, Depends(get_settings)]) -> SqlExecutor:
    return SqlExecutor(
        max_rows=settings.MAX_ROWS,
        timeout_seconds=settings.QUERY_TIMEOUT_SECONDS,
    )


def get_validation_pipeline(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ValidationPipeline:
    return ValidationPipeline.default(settings)


def get_conversation_memory(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConversationMemory:
    return ConversationMemory(redis=request.app.state.redis, ttl_seconds=settings.SESSION_TTL)


async def require_api_key(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """No-op when API_KEY is unset; otherwise enforces an exact match."""
    if not settings.API_KEY:
        return
    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
