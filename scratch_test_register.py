import asyncio
from app.database import AsyncSessionLocal, engine, Base
from app.models import User
from app.schemas import UserCreate
from app.routers.auth import register
from fastapi import BackgroundTasks
from unittest.mock import MagicMock
import sys

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    db = AsyncSessionLocal()
    user_in = UserCreate(email="test_reg@example.com", password="password123", full_name="Test")
    bg_tasks = BackgroundTasks()
    request = MagicMock()
    
    try:
        res = await register(request=request, user_in=user_in, background_tasks=bg_tasks, db=db)
        print("Success:", res)
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)

asyncio.run(main())
