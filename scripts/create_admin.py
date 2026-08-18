import asyncio
from app.database import AsyncSessionLocal
from app.models import User
from app.auth import get_password_hash
import uuid

async def create_admin():
    async with AsyncSessionLocal() as session:
        from sqlalchemy.future import select
        result = await session.execute(select(User).where(User.email == 'admin@insightcircle.com'))
        admin = result.scalars().first()
        if not admin:
            admin = User(
                id=str(uuid.uuid4()),
                email='admin@insightcircle.com',
                password_hash=get_password_hash('admin123'),
                full_name='System Admin',
                role='admin',
                status='active',
                email_verified=True
            )
            session.add(admin)
            await session.commit()
            print("Admin created: admin@insightcircle.com / admin123")
        else:
            print("Admin already exists: admin@insightcircle.com / admin123")

if __name__ == '__main__':
    asyncio.run(create_admin())
