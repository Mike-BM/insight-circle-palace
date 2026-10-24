import asyncio
import os
import sys
import uuid
from datetime import timedelta
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal, Base, engine
from app.models import (
    Program,
    Module,
    Lesson,
    User,
    PaymentAccessRequest,
    ProgramEntitlement,
    utcnow,
)
from main import app


def test_payment_access_control_and_approval_workflow():
    async def _run():
        # Ensure database tables exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as learner_client, \
                   AsyncClient(transport=transport, base_url="http://test") as other_learner_client, \
                   AsyncClient(transport=transport, base_url="http://test") as admin_client, \
                   AsyncClient(transport=transport, base_url="http://test") as anon_client:

            # Create 2 test programs: Program A (Paid) and Program B (Paid)
            prog_a_slug = f"paid-track-{uuid.uuid4().hex[:6]}"
            prog_b_slug = f"paid-track-{uuid.uuid4().hex[:6]}"

            async with AsyncSessionLocal() as session:
                prog_a = Program(
                    id=str(uuid.uuid4()),
                    slug=prog_a_slug,
                    title="Executive AI Architecture",
                    description="Advanced AI strategy for senior technical leaders.",
                    price_kes=4500.0,
                    price_usd=39.0,
                    is_paid=True,
                    payment_instructions="Paybill 522522 Account 1314902847",
                    published=True,
                    is_active=True,
                )
                prog_b = Program(
                    id=str(uuid.uuid4()),
                    slug=prog_b_slug,
                    title="Frontier Venture Finance",
                    description="Venture capital structures and capital deployment.",
                    price_kes=5000.0,
                    price_usd=45.0,
                    is_paid=True,
                    published=True,
                    is_active=True,
                )
                session.add_all([prog_a, prog_b])

                # Add module and lesson to Program A
                mod_a = Module(
                    id=str(uuid.uuid4()),
                    program_id=prog_a.id,
                    title="Module 1: High Performance Systems",
                    order=1,
                )
                session.add(mod_a)

                lesson_a = Lesson(
                    id=str(uuid.uuid4()),
                    module_id=mod_a.id,
                    title="Lesson 1.1: Distributed Compute Fundamentals",
                    order=1,
                    content_type="text",
                    content_body="CONFIDENTIAL_PAID_MATERIAL: Distributed compute architectures rely on partitioned consensus.",
                    video_url="https://secure.video.cdn/lesson-101.m3u8",
                    duration_minutes=35,
                )
                session.add(lesson_a)
                await session.commit()

            # Register accounts
            learner_email = f"learner_{uuid.uuid4().hex[:6]}@example.com"
            other_learner_email = f"other_{uuid.uuid4().hex[:6]}@example.com"
            admin_email = f"admin_{uuid.uuid4().hex[:6]}@example.com"
            pwd = "SecurePassword123!"

            for client, email in [(learner_client, learner_email), (other_learner_client, other_learner_email), (admin_client, admin_email)]:
                r = await client.post("/auth/register", json={"full_name": "Test User", "email": email, "password": pwd})
                assert r.status_code == 201

            # Elevate admin and verify emails
            async with AsyncSessionLocal() as session:
                u_l = (await session.execute(select(User).where(User.email == learner_email))).scalars().first()
                u_o = (await session.execute(select(User).where(User.email == other_learner_email))).scalars().first()
                u_a = (await session.execute(select(User).where(User.email == admin_email))).scalars().first()
                u_l.email_verified = True
                u_o.email_verified = True
                u_a.email_verified = True
                u_a.role = "admin"
                await session.commit()

            # Login clients
            assert (await learner_client.post("/auth/login", json={"email": learner_email, "password": pwd})).status_code == 200
            assert (await other_learner_client.post("/auth/login", json={"email": other_learner_email, "password": pwd})).status_code == 200
            assert (await admin_client.post("/auth/login", json={"email": admin_email, "password": pwd})).status_code == 200

            # 1. Anonymous visitor opening curriculum -> sees outline, but private content is locked
            anon_curr = (await anon_client.get(f"/programs/{prog_a_slug}/curriculum")).json()
            assert anon_curr["title"] == "Executive AI Architecture"
            assert anon_curr["is_entitled"] is False
            assert len(anon_curr["modules"]) == 1
            first_lesson = anon_curr["modules"][0]["lessons"][0]
            assert first_lesson["title"] == "Lesson 1.1: Distributed Compute Fundamentals"
            assert first_lesson["content_body"] is None, "Visitor must not see full lesson content"
            assert first_lesson["video_url"] is None, "Visitor must not see protected video link"

            # 2. Unpaid authenticated learner attempts to enroll directly -> BLOCKED (403 Forbidden)
            enr_fail = await learner_client.post(f"/programs/{prog_a_slug}/enroll")
            assert enr_fail.status_code == 403, f"Expected 403 but got {enr_fail.status_code}"
            detail = enr_fail.json()["detail"].lower()
            assert "paid" in detail or "payment" in detail or "entitlement" in detail

            # 3. Learner submits a manual payment access request
            tx_ref = f"MPESA_{uuid.uuid4().hex[:8].upper()}"
            req_res = await learner_client.post("/api/payments/request-access", json={
                "item_type": "program",
                "program_slug": prog_a_slug,
                "payment_method": "mpesa_manual",
                "transaction_reference": tx_ref,
                "amount": 4500.0,
                "currency": "KES",
                "notes": "Paid via M-Pesa Till 3491023",
            })
            assert req_res.status_code == 200
            req_data = req_res.json()
            request_id = req_data["id"]
            assert req_data["status"] == "pending"
            assert req_data["transaction_reference"] == tx_ref

            # 4. Duplicate request submission prevention
            dup_res = await learner_client.post("/api/payments/request-access", json={
                "item_type": "program",
                "program_slug": prog_a_slug,
                "payment_method": "mpesa_manual",
                "transaction_reference": f"ANOTHER_REF_{uuid.uuid4().hex[:4]}",
                "amount": 4500.0,
            })
            assert dup_res.status_code == 400
            assert "pending access request" in dup_res.json()["detail"]

            # 5. Learner curriculum re-fetch reflects "pending_approval"
            pending_curr = (await learner_client.get(f"/programs/{prog_a_slug}/curriculum")).json()
            assert pending_curr["is_entitled"] is False
            assert pending_curr["entitlement_status"] == "pending_approval"
            assert pending_curr["pending_request"]["transaction_reference"] == tx_ref

            # 6. Unauthorized user attempts to approve payment -> BLOCKED (403)
            hack_res = await other_learner_client.post(f"/api/admin/payment-requests/{request_id}/approve", json={})
            assert hack_res.status_code == 403

            # 7. Admin views pending requests
            admin_list = (await admin_client.get("/api/admin/payment-requests?status=pending")).json()
            assert admin_list["stats"]["pending"] >= 1
            found = any(r["id"] == request_id for r in admin_list["requests"])
            assert found is True

            # 8. Admin approves payment request
            approve_res = await admin_client.post(f"/api/admin/payment-requests/{request_id}/approve", json={
                "admin_notes": "Verified against M-Pesa statement #98231",
            })
            assert approve_res.status_code == 200
            assert approve_res.json()["status"] == "success"

            # 9. Learner now has active entitlement and can access unmasked lesson content
            curr_approved = (await learner_client.get(f"/programs/{prog_a_slug}/curriculum")).json()
            assert curr_approved["is_entitled"] is True
            assert curr_approved["entitlement_status"] == "program_purchase"
            unmasked_lesson = curr_approved["modules"][0]["lessons"][0]
            assert "CONFIDENTIAL_PAID_MATERIAL" in unmasked_lesson["content_body"]
            assert unmasked_lesson["video_url"] == "https://secure.video.cdn/lesson-101.m3u8"

            # 10. Learner attempts to access Program B (which they did not purchase) -> BLOCKED
            curr_b = (await learner_client.get(f"/programs/{prog_b_slug}/curriculum")).json()
            assert curr_b["is_entitled"] is False
            enr_b_fail = await learner_client.post(f"/programs/{prog_b_slug}/enroll")
            assert enr_b_fail.status_code == 403

            # 11. Admin revokes entitlement -> Access is immediately revoked
            ent_id = approve_res.json()["entitlement_id"]
            revoke_res = await admin_client.post(f"/api/admin/entitlements/{ent_id}/revoke")
            assert revoke_res.status_code == 200

            curr_revoked = (await learner_client.get(f"/programs/{prog_a_slug}/curriculum")).json()
            assert curr_revoked["is_entitled"] is False

    asyncio.run(_run())
