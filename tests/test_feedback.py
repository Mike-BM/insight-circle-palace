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
from app.models import Feedback, User
from main import app


def test_feedback_complete_flow():
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Validation test: Invalid ratings
            invalid_res = await ac.post(
                "/api/feedback", json={"rating": 6, "message": "Too high rating"}
            )
            assert invalid_res.status_code == 400

            invalid_res2 = await ac.post(
                "/api/feedback", json={"rating": 0, "message": "Too low rating"}
            )
            assert invalid_res2.status_code == 400

            # 2. Validation test: Empty message
            empty_msg_res = await ac.post(
                "/api/feedback", json={"rating": 5, "message": "   "}
            )
            assert empty_msg_res.status_code == 400

            # 3. Successful Guest Feedback submission
            session_id = f"fb_sess_{uuid.uuid4().hex[:8]}"
            guest_payload = {
                "rating": 5,
                "category": "Certificate Verification",
                "tags": ["📜 Certificate Checking", "⚡ Speed & Performance"],
                "message": "The certificate verification was instant and beautiful! Would love LinkedIn sharing directly.",
                "name": "Sarah Student",
                "email": "sarah@example.com",
                "page_url": "/static/verify.html?code=ICP-2026-TEST",
                "session_id": session_id,
            }

            guest_res = await ac.post("/api/feedback", json=guest_payload)
            assert (
                guest_res.status_code == 201
            ), f"Guest feedback failed: {guest_res.text}"
            res_data = guest_res.json()
            assert res_data["status"] == "ok"
            feedback_id_1 = res_data["id"]

            # 4. Verify in Database
            async with AsyncSessionLocal() as session:
                db_item = await session.get(Feedback, feedback_id_1)
                assert db_item is not None
                assert db_item.rating == 5
                assert db_item.name == "Sarah Student"
                assert db_item.category == "Certificate Verification"
                assert "Certificate Checking" in db_item.tags
                assert db_item.status == "New"

            # 5. Check alias endpoint /api/public/feedback
            alias_res = await ac.post(
                "/api/public/feedback",
                json={
                    "rating": 4,
                    "category": "Programs & Content",
                    "tags": ["📚 Learning & Programs"],
                    "message": "Love the curriculum structure, please add more hands-on AI exercises.",
                    "page_url": "/static/my-programs.html",
                },
            )
            assert alias_res.status_code == 201
            feedback_id_2 = alias_res.json()["id"]

            # 6. Check Unauthorized access to admin endpoints
            unauth_stats = await ac.get("/admin/feedback/stats")
            assert unauth_stats.status_code in (401, 403)

            unauth_list = await ac.get("/admin/feedback")
            assert unauth_list.status_code in (401, 403)

            # 7. Create Admin and Login
            admin_email = f"admin_fb_{uuid.uuid4().hex[:6]}@example.com"
            admin_pw = "FeedbackAdminSecret123!"

            async with AsyncSessionLocal() as session:
                admin_user = User(
                    email=admin_email,
                    password_hash=get_password_hash(admin_pw),
                    full_name="Feedback Supervisor",
                    role="admin",
                    email_verified=True,
                    status="active",
                )
                session.add(admin_user)
                await session.commit()

            login_res = await ac.post(
                "/auth/login", json={"email": admin_email, "password": admin_pw}
            )
            assert login_res.status_code == 200
            assert "insight_session" in login_res.cookies

            # 8. Admin Feedback Stats
            stats_res = await ac.get("/admin/feedback/stats")
            assert stats_res.status_code == 200
            stats = stats_res.json()
            assert stats["total"] >= 2
            assert stats["new_count"] >= 2
            assert stats["average_rating"] > 0
            assert "5" in stats["ratings_breakdown"]

            # 9. Admin List & Filter
            list_res = await ac.get("/admin/feedback?status=New&rating=5")
            assert list_res.status_code == 200
            items = list_res.json()["feedback"]
            matching = [i for i in items if i["id"] == feedback_id_1]
            assert len(matching) == 1
            assert matching[0]["rating"] == 5
            assert matching[0]["name"] == "Sarah Student"

            # 10. Admin Update Status & Notes
            update_res = await ac.put(
                f"/admin/feedback/{feedback_id_1}",
                json={
                    "status": "Reviewed",
                    "admin_notes": "Great suggestion. Created issue for 1-click LinkedIn credential share.",
                },
            )
            assert update_res.status_code == 200
            up_data = update_res.json()
            assert up_data["feedback_status"] == "Reviewed"
            assert "LinkedIn" in up_data["admin_notes"]

            # 11. Admin Delete Feedback
            del_res = await ac.delete(f"/admin/feedback/{feedback_id_2}")
            assert del_res.status_code == 200

            # Verify deletion from DB
            async with AsyncSessionLocal() as session:
                deleted_item = await session.get(Feedback, feedback_id_2)
                assert deleted_item is None

    asyncio.run(_run())


def test_feedback_page_routes():
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res1 = await ac.get("/feedback")
            assert res1.status_code == 200
            assert "Feedback" in res1.text
            assert "Suggestions" in res1.text

            res2 = await ac.get("/feedback.html")
            assert res2.status_code == 200
            assert "Feedback" in res2.text

            res3 = await ac.get("/static/feedback.html")
            assert res3.status_code == 200
            assert "Feedback" in res3.text

    asyncio.run(_run())
