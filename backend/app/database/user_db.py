"""Per-request connections to a user's target database; read-only sessions set ``default_transaction_read_only`` as defense in depth."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.drivers import ConnectionCredentials
from app.drivers.postgres import _ssl_arg


@asynccontextmanager
async def user_db_session(
    creds: ConnectionCredentials, *, read_only: bool = True
) -> AsyncIterator[AsyncSession]:
    url = URL.create(
        "postgresql+asyncpg",
        username=creds.username,
        password=creds.password,
        host=creds.host,
        port=creds.port,
        database=creds.database,
    )
    server_settings: dict[str, str] = {}
    if read_only:
        server_settings["default_transaction_read_only"] = "on"

    connect_args: dict = {"ssl": _ssl_arg(creds.ssl_mode)}
    if server_settings:
        connect_args["server_settings"] = server_settings

    engine = create_async_engine(url, poolclass=NullPool, connect_args=connect_args)
    try:
        async with async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )() as session:
            yield session
    finally:
        await engine.dispose()
