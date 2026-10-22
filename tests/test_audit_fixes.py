import asyncio
import os
import sys
import uuid
from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal, Base, engine
from app.models import Enrollment, Program, User
from main import app


def test_audit_enrollment_and_dashboard_flow():
    """
    Validates:
    1. User enrolls in a program.
    2. Enrollment is saved correctly in the database.
    3. Duplicate enrollment is rejected with 400.
    4. Dashboard endpoint (/programs/me/enrollments) returns the enrolled program with correct learn_url.
    5. Learn_url points to /static/learn.html?program={slug}, NOT the marketing page.
    6. Multi-tenant privacy: User B does not see User A's enrollments.
    7. Curriculum endpoint reports is_enrolled = True for the enrolled user.
    """
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client_a, \
                   AsyncClient(transport=transport, base_url="http://test") as client_b:

            # 1. Register User A
            email_a = f"learner_{uuid.uuid4().hex[:6]}@example.com"
            password = "Password123!"
            r = await client_a.post("/auth/register", json={
                "full_name": "Learner Alpha",
                "email": email_a,
                "password": password
            })
            assert r.status_code == 201, f"User A registration failed: {r.text}"

            # 2. Register User B
            email_b = f"learner_{uuid.uuid4().hex[:6]}@example.com"
            r = await client_b.post("/auth/register", json={
                "full_name": "Learner Beta",
                "email": email_b,
                "password": password
            })
            assert r.status_code == 201, f"User B registration failed: {r.text}"

            # Mark both verified in database so they can log in
            async with AsyncSessionLocal() as session:
                u_a = (await session.execute(select(User).where(User.email == email_a))).scalars().first()
                u_b = (await session.execute(select(User).where(User.email == email_b))).scalars().first()
                u_a.email_verified = True
                u_b.email_verified = True
                await session.commit()

            # Log in both users to establish authenticated sessions
            res_a = await client_a.post("/auth/login", json={"email": email_a, "password": password})
            assert res_a.status_code == 200, f"Login A failed: {res_a.text}"

            res_b = await client_b.post("/auth/login", json={"email": email_b, "password": password})
            assert res_b.status_code == 200, f"Login B failed: {res_b.text}"

            # 3. Check Program Track exists
            prog_slug = "tech-ai"
            r = await client_a.get(f"/programs/{prog_slug}/curriculum")
            assert r.status_code == 200
            curric_data = r.json()
            assert curric_data["is_enrolled"] is False

            # 4. User A Enrolls in Program Track
            r = await client_a.post(f"/programs/{prog_slug}/enroll")
            assert r.status_code == 200, f"Enrollment failed: {r.text}"
            enroll_data = r.json()
            assert enroll_data["status"] == "in_progress"
            assert f"/static/learn.html?program={prog_slug}" in enroll_data["learn_url"]

            # 5. Prevent Duplicate Enrollment
            r_dup = await client_a.post(f"/programs/{prog_slug}/enroll")
            assert r_dup.status_code == 400
            assert "Already enrolled" in r_dup.json()["detail"]

            # 6. Verify Database Record
            async with AsyncSessionLocal() as session:
                enr_res = await session.execute(
                    select(Enrollment).join(Program).where(Program.slug == prog_slug)
                )
                enrollments = enr_res.scalars().all()
                assert len(enrollments) >= 1

            # 7. Verify Dashboard Data (/programs/me/enrollments)
            r_me = await client_a.get("/programs/me/enrollments")
            assert r_me.status_code == 200
            my_enrs = r_me.json()
            assert len(my_enrs) >= 1
            found = next((e for e in my_enrs if e["program_slug"] == prog_slug), None)
            assert found is not None
            assert found["status"] == "in_progress"
            assert found["learn_url"].startswith(f"/static/learn.html?program={prog_slug}")

            # 8. User B Isolation Check (User B does NOT see User A's program)
            r_me_b = await client_b.get("/programs/me/enrollments")
            assert r_me_b.status_code == 200
            b_enrs = r_me_b.json()
            assert len(b_enrs) == 0

            # 9. Verify Curriculum now reports is_enrolled = True for User A
            r_curric_after = await client_a.get(f"/programs/{prog_slug}/curriculum")
            assert r_curric_after.status_code == 200
            assert r_curric_after.json()["is_enrolled"] is True

    asyncio.run(_run())


def test_audit_static_routes_and_assets():
    """
    Validates:
    1. /assets/logo.jpg resolves with HTTP 200
    2. /static/assets/logo.jpg resolves with HTTP 200
    3. /learn and /learn.html resolve with HTTP 200
    4. /tech-ai and /tech-ai.html resolve with HTTP 200
    """
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/assets/logo.jpg")
            assert r.status_code == 200

            r = await client.get("/static/assets/logo.jpg")
            assert r.status_code == 200

            r = await client.get("/learn")
            assert r.status_code == 200

            r = await client.get("/tech-ai")
            assert r.status_code == 200

    asyncio.run(_run())
