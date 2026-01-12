from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import get_rw_session_factory


async def get_rw_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an app-database session."""
    async with get_rw_session_factory()() as session:
        yield session
