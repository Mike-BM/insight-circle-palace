import asyncio
import base64
import io
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.future import select

from app.database import AsyncSessionLocal, Base, engine
from app.models import EmailVerificationToken, User
from main import app


def test_auth_flow():
    async def _run():
        transport = ASGITransport(app=app)
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        password = "Password123!"
        full_name = "Auth Flow Tester"

        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Register User
            reg_res = await ac.post(
                "/auth/register",
                json={"full_name": full_name, "email": email, "password": password},
            )
            assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"
            assert "verification link" in reg_res.json()["message"]

            # 2. Verify user exists in database and mark email_verified = True
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(User).where(User.email == email))
                user = result.scalars().first()
                assert user is not None, "User was not created in database"
                assert user.full_name == full_name
                assert user.email_verified is False

                # Check verification token
                tok_result = await session.execute(
                    select(EmailVerificationToken).where(
                        EmailVerificationToken.user_id == user.id
                    )
                )
                tok = tok_result.scalars().first()
                assert tok is not None, "Verification token was not created"

                # Mark verified for login test
                user.email_verified = True
                await session.commit()

            # 3. Login
            login_res = await ac.post(
                "/auth/login", json={"email": email, "password": password}
            )
            assert login_res.status_code == 200, f"Login failed: {login_res.text}"
            assert "insight_session" in login_res.cookies

            # 4. Check /auth/me
            me_res = await ac.get("/auth/me")
            assert me_res.status_code == 200, f"Auth me failed: {me_res.text}"
            user_data = me_res.json()
            assert user_data["email"] == email
            assert user_data["full_name"] == full_name

            # 5. Submit Intake Form
            submit_res = await ac.post(
                "/applications/submit",
                json={
                    "username": "testuser",
                    "q1_curiosity": "Curious about self-growth",
                    "q2_awareness": "Mindset development",
                    "q3_mindset": "Continuous learning",
                    "q4_reflection": "Overcame a difficult project",
                    "q5_focus": "Tech & AI",
                },
            )
            assert (
                submit_res.status_code == 200
            ), f"Intake submission failed: {submit_res.text}"
            data = submit_res.json()
            assert data["status"] == "success"
            assert "path" in data

            # 6. Check /applications/me
            my_app_res = await ac.get("/applications/me")
            assert my_app_res.status_code == 200
            assert my_app_res.json()["has_application"] is True

    asyncio.run(_run())


def test_registration_honeypot():
    async def _run():
        transport = ASGITransport(app=app)
        bot_email = f"bot_{uuid.uuid4().hex[:8]}@example.com"

        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post(
                "/auth/register",
                json={
                    "full_name": "Spam Bot",
                    "email": bot_email,
                    "password": "botpassword123",
                    "honeypot": "i_am_a_bot",
                },
            )
            assert res.status_code == 201
            assert "verification link" in res.json()["message"]

            # Ensure bot is NOT in DB
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).where(User.email == bot_email)
                )
                assert result.scalars().first() is None

    asyncio.run(_run())


def test_image_compression_and_upload():
    async def _run():
        transport = ASGITransport(app=app)
        email = f"photo_test_{uuid.uuid4().hex[:8]}@example.com"
        password = "Password123!"

        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Register and verify
            await ac.post(
                "/auth/register",
                json={
                    "full_name": "Photo Tester",
                    "email": email,
                    "password": password,
                },
            )
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(User).where(User.email == email))
                u = res.scalars().first()
                u.email_verified = True
                await session.commit()

            # Login
            await ac.post("/auth/login", json={"email": email, "password": password})

            # Create an 800x600 test JPEG image
            img_buf = io.BytesIO()
            original_img = Image.new("RGB", (800, 600), color="teal")
            original_img.save(img_buf, format="JPEG")
            img_bytes = img_buf.getvalue()

            # Upload photo
            upload_res = await ac.post(
                "/auth/me/photo",
                files={"file": ("avatar.jpg", img_bytes, "image/jpeg")},
            )
            assert (
                upload_res.status_code == 200
            ), f"Upload photo failed: {upload_res.text}"
            user_data = upload_res.json()
            assert "photo_url" in user_data
            photo_url = user_data["photo_url"]

            # Check that it compressed to WebP data URL
            assert photo_url.startswith(
                "data:image/webp;base64,"
            ), "photo_url should be compressed to webp"

            # Decode and verify dimensions compressed to <= 400x400
            b64_str = photo_url.split("data:image/webp;base64,")[1]
            compressed_bytes = base64.b64decode(b64_str)
            compressed_img = Image.open(io.BytesIO(compressed_bytes))

            assert compressed_img.format == "WEBP"
            assert compressed_img.width <= 400
            assert compressed_img.height <= 400

            # Test invalid file rejection
            invalid_res = await ac.post(
                "/auth/me/photo",
                files={"file": ("test.txt", b"not an image", "text/plain")},
            )
            assert invalid_res.status_code == 400

    asyncio.run(_run())


def test_login_logout_lifecycle():
    async def _run():
        transport = ASGITransport(app=app)
        email = f"lifecycle_{uuid.uuid4().hex[:8]}@example.com"
        password = "Password123!"
        full_name = "Lifecycle Tester"

        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Register & verify user
            reg_res = await ac.post(
                "/auth/register",
                json={"full_name": full_name, "email": email, "password": password},
            )
            assert reg_res.status_code == 201

            async with AsyncSessionLocal() as session:
                res = await session.execute(select(User).where(User.email == email))
                u = res.scalars().first()
                u.email_verified = True
                await session.commit()

            # 2. Login
            login_res = await ac.post(
                "/auth/login", json={"email": email, "password": password}
            )
            assert login_res.status_code == 200
            data = login_res.json()
            assert data["message"] == "Logged in successfully"
            assert data["user"]["email"] == email
            assert data["user"]["role"] == "member"
            assert "insight_session" in login_res.cookies

            # 3. Access protected route
            me_res = await ac.get("/auth/me")
            assert me_res.status_code == 200
            assert me_res.json()["email"] == email

            # 4. Logout
            logout_res = await ac.post("/auth/logout")
            assert logout_res.status_code == 200
            assert logout_res.json()["message"] == "Logged out successfully"

            # 5. Verify /auth/me is now unauthorized
            me_after = await ac.get("/auth/me")
            assert me_after.status_code == 401

            # 6. Calling logout again when already logged out must succeed cleanly (idempotent)
            logout_again = await ac.post("/auth/logout")
            assert logout_again.status_code == 200

            # 7. Admin login and logout lifecycle
            admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
            from app.auth import get_password_hash

            async with AsyncSessionLocal() as session:
                admin_user = User(
                    email=admin_email,
                    password_hash=get_password_hash("AdminPass123!"),
                    full_name="Admin Lifecycle Tester",
                    role="admin",
                    email_verified=True,
                    status="active",
                )
                session.add(admin_user)
                await session.commit()

            admin_login = await ac.post(
                "/auth/login", json={"email": admin_email, "password": "AdminPass123!"}
            )
            assert admin_login.status_code == 200
            assert admin_login.json()["user"]["role"] == "admin"

            admin_users = await ac.get("/admin/users")
            assert admin_users.status_code == 200

            admin_logout = await ac.post("/auth/logout")
            assert admin_logout.status_code == 200

            admin_users_after = await ac.get("/admin/users")
            assert admin_users_after.status_code == 401

    asyncio.run(_run())
