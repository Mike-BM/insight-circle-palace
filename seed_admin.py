import asyncio
from app.database import AsyncSessionLocal
from app.models import User
from app.auth import get_password_hash

async def seed_admin():
    async with AsyncSessionLocal() as db:
        user = User(
            email='admin@insightcircle.com',
            password_hash=get_password_hash('admin123'),
            full_name='Admin User',
            role='admin',
            email_verified=True,
            status='active'
        )
        db.add(user)
        await db.commit()
        print('Admin user created successfully.')

if __name__ == "__main__":
    asyncio.run(seed_admin())
