import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import Program

async def test():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Program))
        programs = result.scalars().all()
        for p in programs:
            print(f"Program: {p.slug}, active: {p.is_active}")

asyncio.run(test())
