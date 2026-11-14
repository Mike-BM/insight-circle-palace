"""Create (or report) a single admin account.

Usage (the password is NEVER hardcoded):
    ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='a-long-unique-passphrase' python scripts/create_admin.py

The account is created with must_change_password=True so the password is changed at first login.
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import get_password_hash
from app.database import AsyncSessionLocal
from app.models import User
from app.security import validate_password_strength


async def create_admin():
    email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD") or ""
    if not email or not password:
        sys.exit("Set ADMIN_EMAIL and ADMIN_PASSWORD environment variables first.")
    try:
        validate_password_strength(password)
    except ValueError as e:
        sys.exit(f"Refusing weak password: {e}")
    if len(password) < 12:
        sys.exit("Admin passwords must be at least 12 characters.")

    async with AsyncSessionLocal() as session:
        from sqlalchemy.future import select

        result = await session.execute(select(User).where(User.email == email))
        admin = result.scalars().first()
        if not admin:
            admin = User(
                id=str(uuid.uuid4()),
                email=email,
                password_hash=get_password_hash(password),
                full_name="System Admin",
                role="admin",
                status="active",
                email_verified=True,
                must_change_password=True,
            )
            session.add(admin)
            await session.commit()
            print(f"Admin created: {email} (password change required at first login)")
        else:
            print(f"Admin already exists: {email} (nothing changed)")


if __name__ == "__main__":
    asyncio.run(create_admin())
