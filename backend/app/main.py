"""FastAPI app factory plus lifespan that owns DB engines and the Redis client."""

from __future__ import annotations

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import structlog
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.middleware import RequestContextMiddleware
from app.api.rate_limit import limiter, rate_limit_handler
from app.api.router import api_router
from app.config.settings import get_settings
from app.database.engine import close_engines, get_rw_engine, init_engines
from app.utils.logging import configure_logging
from app.utils.tracing import (
    configure_tracing,
    instrument_fastapi,
    instrument_sqlalchemy,
)

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    configure_logging(settings.LOG_LEVEL)
    configure_tracing(
        service_name=settings.APP_NAME,
        otlp_endpoint=settings.OTEL_ENDPOINT,
        version=settings.VERSION,
    )

    init_engines(settings)
    app.state.redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )

    # Best-effort arq pool; services fall back to inline execution if Redis is down.
    try:
        app.state.arq = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    except Exception:
        app.state.arq = None
        log.warning("arq.pool_unavailable")

    if settings.OTEL_ENABLE_INSTRUMENTATION:
        instrument_fastapi(app)
        instrument_sqlalchemy(get_rw_engine())

    log.info(
        "app.started",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )

    try:
        yield
    finally:
        await close_engines()
        if getattr(app.state, "arq", None) is not None:
            await app.state.arq.aclose()
        await app.state.redis.aclose()
        log.info("app.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="QueryMind",
        description=(
            "Natural-language to SQL agent with LangGraph self-correction, "
            "live pipeline streaming, multi-turn memory, and result visualization."
        ),
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


app = create_app()
