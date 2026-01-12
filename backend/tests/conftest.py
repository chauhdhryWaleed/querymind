import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.fixtures.sample_schema import SAMPLE_SCHEMA


@pytest.fixture(scope="session")
def sample_schema() -> dict:
    return SAMPLE_SCHEMA


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client against the real FastAPI app (no live DB required for unit tests)."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
