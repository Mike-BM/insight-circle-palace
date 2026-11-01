import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.future import select

from app.auth import get_password_hash
from app.database import AsyncSessionLocal
from app.models import User

DEFAULT_PW = os.environ.get("ADMIN_INITIAL_PASSWORD", "Admin123!")
if DEFAULT_PW == "Admin123!":
    print("Notice: Using default temporary password (Admin123!). Set ADMIN_INITIAL_PASSWORD env var in production.")

ADMIN_ACCOUNTS = [
    {
        "email": "brianmuema928@gmail.com",
        "full_name": "Brian Muema",
        "role": "super_admin",
        "temp_password": DEFAULT_PW,
        "phone": "+254 700 000001",
        "bio": "Principal Administrator for Insight Circle Palace platform.",
    },
    {
        "email": "rayazenlyx@gmail.com",
        "full_name": "Raya Zenlyx",
        "role": "super_admin",
        "temp_password": DEFAULT_PW,
        "phone": "+254 700 000002",
        "bio": "Super Administrator overseeing platform operations and security.",
    },
    {
        "email": "admin@insightcircle.com",
        "full_name": "Insight Chief Admin",
        "role": "super_admin",
        "temp_password": DEFAULT_PW,
        "phone": "+254 700 000003",
        "bio": "System Administrator for Insight Circle Palace platform.",
    },
]


async def seed_admins():
    async with AsyncSessionLocal() as session:
        print(
            "--- Seeding 3 Admin Accounts with Forced First-Login Password Change ---"
        )
        for admin_info in ADMIN_ACCOUNTS:
            stmt = select(User).where(User.email == admin_info["email"])
            res = await session.execute(stmt)
            existing_user = res.scalar_one_or_none()

            hashed_pw = get_password_hash(admin_info["temp_password"])

            if existing_user:
                print(f"Updating existing admin: {admin_info['email']}")
                existing_user.full_name = admin_info["full_name"]
                existing_user.role = admin_info["role"]
                existing_user.password_hash = hashed_pw
                existing_user.status = "active"
                existing_user.email_verified = True
                existing_user.must_change_password = True
                existing_user.phone = admin_info.get("phone")
                existing_user.bio = admin_info.get("bio")
            else:
                print(f"Creating new admin: {admin_info['email']}")
                new_admin = User(
                    email=admin_info["email"],
                    full_name=admin_info["full_name"],
                    role=admin_info["role"],
                    password_hash=hashed_pw,
                    status="active",
                    email_verified=True,
                    must_change_password=True,
                    phone=admin_info.get("phone"),
                    bio=admin_info.get("bio"),
                )
                session.add(new_admin)

        await session.commit()
        print("\nAll 3 admins seeded successfully!")
        print("Credentials for all 3 admins:")
        for admin_info in ADMIN_ACCOUNTS:
            print(
                f" - Email: {admin_info['email']} | Temp Password: {admin_info['temp_password']} | Role: {admin_info['role']} | must_change_password: True"
            )


if __name__ == "__main__":
    asyncio.run(seed_admins())
