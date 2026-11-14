import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.future import select

from app.auth import get_password_hash
from app.database import AsyncSessionLocal
from app.models import User

# SECURITY: no built-in default password. Provide ADMIN_INITIAL_PASSWORD (12+ chars) yourself.
DEFAULT_PW = (os.environ.get("ADMIN_INITIAL_PASSWORD") or "").strip()
if len(DEFAULT_PW) < 12:
    sys.exit("Set ADMIN_INITIAL_PASSWORD (at least 12 characters) before running this script.")

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
        print("Accounts (password is the ADMIN_INITIAL_PASSWORD you provided):")
        for admin_info in ADMIN_ACCOUNTS:
            print(
                f" - Email: {admin_info['email']} | Role: {admin_info['role']} | must_change_password: True"
            )


if __name__ == "__main__":
    asyncio.run(seed_admins())
