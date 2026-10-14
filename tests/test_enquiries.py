import asyncio
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

from app.auth import get_password_hash
from app.database import AsyncSessionLocal, Base, engine
from app.models import ContactEnquiry, User
from main import app


def test_enquiries_flow():
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Public Settings verification
            settings_res = await ac.get("/api/public/settings")
            assert settings_res.status_code == 200
            s_data = settings_res.json()
            assert "whatsapp-number" in s_data
            assert "support-phone" in s_data
            assert "support-email" in s_data

            # 2. Submit Public Chat Enquiry
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
            payload = {
                "name": "Jane Visitor",
                "email": "jane.visitor@example.com",
                "phone": "+254700112233",
                "message": "Hello, I want to learn more about the Career Acceleration program!",
                "source": "website_chat",
                "session_id": session_id,
            }
            create_res = await ac.post("/api/public/enquiries", json=payload)
            assert create_res.status_code == 201, f"Enquiry failed: {create_res.text}"
            enquiry_data = create_res.json()
            assert enquiry_data["id"] is not None
            assert enquiry_data["status"] == "ok"
            enquiry_id = enquiry_data["id"]

            # 3. Verify in Database
            async with AsyncSessionLocal() as session:
                db_res = await session.execute(
                    select(ContactEnquiry).where(ContactEnquiry.id == enquiry_id)
                )
                db_enq = db_res.scalars().first()
                assert db_enq is not None
                assert db_enq.name == "Jane Visitor"
                assert db_enq.status == "New"
                assert db_enq.source == "website_chat"
                assert db_enq.session_id == session_id

            # 4. Unauthorized Admin access check
            unauth_res = await ac.get("/admin/enquiries/stats")
            assert unauth_res.status_code in (401, 403)

            # 5. Create or verify an Admin user and log in
            admin_email = f"admin_{uuid.uuid4().hex[:6]}@example.com"
            admin_password = "AdminSecret123!"
            async with AsyncSessionLocal() as session:
                admin_user = User(
                    email=admin_email,
                    password_hash=get_password_hash(admin_password),
                    full_name="Admin System",
                    role="admin",
                    email_verified=True,
                    status="active",
                )
                session.add(admin_user)
                await session.commit()

            login_res = await ac.post(
                "/auth/login", json={"email": admin_email, "password": admin_password}
            )
            assert login_res.status_code == 200
            assert "insight_session" in login_res.cookies

            # 6. Admin stats
            stats_res = await ac.get("/admin/enquiries/stats")
            assert stats_res.status_code == 200
            stats = stats_res.json()
            assert stats["total"] >= 1
            assert stats["new"] >= 1

            # 7. Admin list enquiries
            list_res = await ac.get("/admin/enquiries?status=New")
            assert list_res.status_code == 200
            items = list_res.json()["enquiries"]
            matching = [i for i in items if i["id"] == enquiry_id]
            assert len(matching) == 1

            # 8. Update enquiry status & admin notes
            update_res = await ac.put(
                f"/admin/enquiries/{enquiry_id}",
                json={
                    "status": "Responded",
                    "admin_notes": "Contacted visitor via WhatsApp on 2026-09-09.",
                },
            )
            assert update_res.status_code == 200
            updated_data = update_res.json()
            assert updated_data["enquiry_status"] == "Responded"
            assert "Contacted visitor" in (updated_data["admin_notes"] or "")

            # 9. Delete enquiry
            del_res = await ac.delete(f"/admin/enquiries/{enquiry_id}")
            assert del_res.status_code == 200

            # Verify deleted from DB
            async with AsyncSessionLocal() as session:
                chk_res = await session.execute(
                    select(ContactEnquiry).where(ContactEnquiry.id == enquiry_id)
                )
                assert chk_res.scalars().first() is None

    asyncio.run(_run())
