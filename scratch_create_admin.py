import asyncio
import os
import sys
sys.path.append(os.getcwd())
from app.database import AsyncSessionLocal
from app.models import User
from sqlalchemy.future import select
import bcrypt

async def create_admin():
    async with AsyncSessionLocal() as session:
        # Check if user exists
        result = await session.execute(select(User).filter(User.email == "admin@insightcircle.com"))
        user = result.scalars().first()
        
        hashed_password = bcrypt.hashpw("Admin@123!".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        if user:
            user.password_hash = hashed_password
            user.role = "admin"
            print("Updated existing admin@insightcircle.com user")
        else:
            user = User(
                email="admin@insightcircle.com",
                password_hash=hashed_password,
                full_name="System Admin",
                role="admin",
                status="active"
            )
            session.add(user)
            print("Created new admin@insightcircle.com user")
        
        await session.commit()
        print("Success! Credentials:")
        print("Email: admin@insightcircle.com")
        print("Password: Admin@123!")

asyncio.run(create_admin())
