import asyncio
import pytest
from app.database import Base, engine
from main import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    async def _init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(_init_db())
    yield

@pytest.fixture(autouse=True)
def disable_rate_limiting():
    if hasattr(app.state, "limiter"):
        app.state.limiter.enabled = False
    yield
    if hasattr(app.state, "limiter"):
        app.state.limiter.enabled = True
