"""arq worker entrypoint: ``arq app.jobs.worker.WorkerSettings``."""

from __future__ import annotations

from arq.connections import RedisSettings

from app.config.settings import get_settings
from app.database.engine import close_engines, init_engines
from app.jobs.email import send_email
from app.jobs.fk_weights import bump_fk_weights
from app.jobs.index_schema import index_connection_schema


async def startup(ctx: dict) -> None:
    settings = get_settings()
    ctx["settings"] = settings
    init_engines(settings)  # jobs use get_rw_session_factory()


async def shutdown(ctx: dict) -> None:
    await close_engines()


class WorkerSettings:
    """arq discovers this class by name."""

    functions: list = [send_email, index_connection_schema, bump_fk_weights]
    redis_settings = RedisSettings.from_dsn(get_settings().REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
