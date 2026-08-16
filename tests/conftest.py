import os
import asyncio
import pytest

# Require TEST_DATABASE_URL be set by caller/CI for a real PostgreSQL test database
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("Please set TEST_DATABASE_URL environment variable for tests")

# Ensure the application uses the test database
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["APP_ENV"] = "testing"

# Import app after env is configured so app.database picks up TEST_DATABASE_URL
from main import app
from fastapi.testclient import TestClient
import app.services.email as email_service
from app.database import engine, Base

async def _reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

# Create a clean database schema once per test session
@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    asyncio.run(_reset_db())
    yield
    asyncio.run(_reset_db())

# Provide a TestClient instance and mock external email sending
@pytest.fixture
def client(monkeypatch):
    # Prevent real emails from being sent during tests
    monkeypatch.setattr(email_service, "send_email", lambda *a, **k: None)

    with TestClient(app) as c:
        yield c
