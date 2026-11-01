import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import declarative_base

# Use DATABASE_URL if available (for production like Postgres on Supabase)
# Fallback to local sqlite for development
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./insight_circle.db")

# On Windows, psycopg async on older Python versions required SelectorEventLoop instead of default ProactorEventLoop
if sys.platform == "win32" and "psycopg" in DATABASE_URL and sys.version_info < (3, 14):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception as e:
        print(f"Could not set WindowsSelectorEventLoopPolicy: {e}")

# If using Postgres, we want to ensure the URL driver is asyncpg
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

if "postgresql+asyncpg://" in DATABASE_URL:
    # Remove sslmode and channel_binding if passed from environment
    DATABASE_URL = DATABASE_URL.replace("sslmode=require", "").replace(
        "channel_binding=require", ""
    )
    DATABASE_URL = DATABASE_URL.replace("?&", "?").replace("&&", "&")
    if DATABASE_URL.endswith("?"):
        DATABASE_URL = DATABASE_URL[:-1]

    if "ssl=" not in DATABASE_URL:
        if "?" in DATABASE_URL:
            DATABASE_URL += "&ssl=require"
        else:
            DATABASE_URL += "?ssl=require"

# SQLite needs connect_args={"check_same_thread": False}
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine_kwargs = {"echo": False}
if "postgresql" in DATABASE_URL:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300  # 5 minutes, prevent idle connection drops
    connect_args["statement_cache_size"] = (
        0  # Required for PgBouncer/Supabase pooler compatibility
    )

engine = create_async_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
