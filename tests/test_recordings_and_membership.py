import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal, Base, engine
from app.models import User, Recording, Membership, PaymentSubmission, MondayRegistration, AuditLog
from main import app


def test_public_recordings_catalogue_masks_protected_sources():
    """
    Validates:
    1. Public visitors can fetch recordings catalogue without authentication.
    2. Draft recordings are not shown to public.
    3. Google Drive file IDs and custom URLs are strictly excluded from the public response.
    4. Protected recordings show has_playback_access = False.
    5. Free recordings show has_playback_access = True.
    """
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as session:
            # Create a published members_only recording
            rec_mem = Recording(
                title=f"Advanced AI Strategy Masterclass {uuid.uuid4().hex[:4]}",
                session_date=datetime.now(timezone.utc),
                description="Deep dive into AI systems architecture.",
                video_source_type="google_drive",
                drive_file_id="1a2b3c4d5e6f7g8h9i0j_SECRET_DRIVE_ID",
                access_requirement="members_only",
                published=True,
            )
            # Create a published free recording
            rec_free = Recording(
                title=f"Public Orientation Session {uuid.uuid4().hex[:4]}",
                session_date=datetime.now(timezone.utc),
                description="Welcome to ICP.",
                video_source_type="google_drive",
                drive_file_id="1x2y3z_PUBLIC_DRIVE_ID",
                access_requirement="free",
                published=True,
            )
            # Create an unpublished draft recording
            rec_draft = Recording(
                title=f"Unreleased Draft Session {uuid.uuid4().hex[:4]}",
                session_date=datetime.now(timezone.utc),
                description="Internal draft.",
                video_source_type="google_drive",
                drive_file_id="1draft_id",
                access_requirement="members_only",
                published=False,
            )
            session.add_all([rec_mem, rec_free, rec_draft])
            await session.commit()
            await session.refresh(rec_mem)
            await session.refresh(rec_free)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/recordings")
            assert res.status_code == 200, res.text
            items = res.json()

            # Draft session should not be in public listing
            titles = [i["title"] for i in items]
            assert rec_draft.title not in titles
            assert rec_mem.title in titles
            assert rec_free.title in titles

            # Check that public response does NOT expose drive_file_id or video_url keys at all
            mem_item = next(i for i in items if i["id"] == rec_mem.id)
            assert "drive_file_id" not in mem_item, "drive_file_id must not be exposed in public catalogue"
            assert "video_url" not in mem_item, "video_url must not be exposed in public catalogue"
            assert mem_item["has_playback_access"] is False
            assert mem_item["access_requirement"] == "members_only"

            # Free item has playback access flag set to True
            free_item = next(i for i in items if i["id"] == rec_free.id)
            assert "drive_file_id" not in free_item
            assert free_item["has_playback_access"] is True
            assert free_item["access_requirement"] == "free"

    asyncio.run(_run())


def test_recording_playback_authorization_and_membership_enforcement():
    """
    Validates:
    1. Unauthenticated request to /playback returns 401.
    2. Authenticated user without active membership returns 403.
    3. User with active membership gets 200 and authorized embed_url with drive_file_id.
    4. User with expired membership is denied playback (403).
    """
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # 1. Setup recording
        async with AsyncSessionLocal() as session:
            rec = Recording(
                title=f"Exclusive Executive Briefing {uuid.uuid4().hex[:4]}",
                description="Confidential session for verified members.",
                video_source_type="google_drive",
                drive_file_id="1ExclusiveDriveFileId1234567890",
                access_requirement="members_only",
                published=True,
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            rec_id = rec.id

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as anon_client, \
                   AsyncClient(transport=transport, base_url="http://test") as unpaid_client, \
                   AsyncClient(transport=transport, base_url="http://test") as paid_client, \
                   AsyncClient(transport=transport, base_url="http://test") as expired_client:

            # 1. Anonymous request -> 401
            r_anon = await anon_client.get(f"/api/recordings/{rec_id}/playback")
            assert r_anon.status_code == 401

            # 2. Register & Login Unpaid User
            email_unpaid = f"unpaid_{uuid.uuid4().hex[:6]}@example.com"
            await unpaid_client.post("/auth/register", json={
                "full_name": "Unpaid User", "email": email_unpaid, "password": "Password123!"
            })
            async with AsyncSessionLocal() as session:
                u = (await session.execute(select(User).where(User.email == email_unpaid))).scalars().first()
                u.email_verified = True
                await session.commit()

            login_res = await unpaid_client.post("/auth/login", json={"email": email_unpaid, "password": "Password123!"})
            assert login_res.status_code == 200

            # Attempt playback -> 403
            r_unpaid = await unpaid_client.get(f"/api/recordings/{rec_id}/playback")
            assert r_unpaid.status_code == 403
            assert "membership" in r_unpaid.json()["detail"].lower()

            # 3. Register & Login Paid User
            email_paid = f"paid_{uuid.uuid4().hex[:6]}@example.com"
            await paid_client.post("/auth/register", json={
                "full_name": "Paid Member", "email": email_paid, "password": "Password123!"
            })
            async with AsyncSessionLocal() as session:
                u_paid = (await session.execute(select(User).where(User.email == email_paid))).scalars().first()
                u_paid.email_verified = True

                # Grant active membership
                mem = Membership(
                    user_id=u_paid.id,
                    status="active",
                    fee_paid=1500.0,
                    currency="KES",
                    activated_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                    granted_by=1
                )
                session.add(mem)
                await session.commit()

            login_paid = await paid_client.post("/auth/login", json={"email": email_paid, "password": "Password123!"})
            assert login_paid.status_code == 200

            r_paid = await paid_client.get(f"/api/recordings/{rec_id}/playback")
            assert r_paid.status_code == 200, r_paid.text
            playback_data = r_paid.json()
            assert playback_data["drive_file_id"] == "1ExclusiveDriveFileId1234567890"
            assert "drive.google.com/file/d/1ExclusiveDriveFileId1234567890/preview" in playback_data["embed_url"]

            # 4. Register & Login Expired User
            email_expired = f"expired_{uuid.uuid4().hex[:6]}@example.com"
            await expired_client.post("/auth/register", json={
                "full_name": "Expired Member", "email": email_expired, "password": "Password123!"
            })
            async with AsyncSessionLocal() as session:
                u_exp = (await session.execute(select(User).where(User.email == email_expired))).scalars().first()
                u_exp.email_verified = True

                mem_exp = Membership(
                    user_id=u_exp.id,
                    status="active",
                    fee_paid=1500.0,
                    currency="KES",
                    activated_at=datetime.now(timezone.utc) - timedelta(days=60),
                    expires_at=datetime.now(timezone.utc) - timedelta(days=30),
                    granted_by=1
                )
                session.add(mem_exp)
                await session.commit()

            login_exp = await expired_client.post("/auth/login", json={"email": email_expired, "password": "Password123!"})
            assert login_exp.status_code == 200

            r_exp = await expired_client.get(f"/api/recordings/{rec_id}/playback")
            assert r_exp.status_code == 403
            assert "expired" in r_exp.json()["detail"].lower()

    asyncio.run(_run())


def test_monday_session_registration_is_free_and_open():
    """
    Validates:
    1. Monday session registration is completely open without authentication or membership.
    2. Successful registration returns confirmed registration status and session details.
    3. Duplicate registration is gracefully handled without exposing other users' details.
    4. Registering for Monday session does NOT grant membership access to past recordings.
    """
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = f"attendee_{uuid.uuid4().hex[:6]}@example.com"
            session_date = "2026-11-02"

            # 1. Register for Monday session without auth
            reg_payload = {
                "session_date": session_date,
                "full_name": "Grace Hopper",
                "email": email,
                "phone": "+254712345678",
                "notes": "Looking forward to the masterclass."
            }
            res = await client.post("/api/monday-sessions/register", json=reg_payload)
            assert res.status_code == 201, res.text
            data = res.json()
            assert data["status"] == "registered"
            assert data["session_date"] == session_date

            # 2. Duplicate registration attempt -> returns already_registered gracefully without info leak
            res_dup = await client.post("/api/monday-sessions/register", json=reg_payload)
            assert res_dup.status_code == 201 or res_dup.status_code == 200
            dup_data = res_dup.json()
            assert dup_data["status"] == "already_registered"
            assert "full_name" not in dup_data, "Must not leak full_name or personal data"

            # 3. Verify in database that NO membership was created
            async with AsyncSessionLocal() as session:
                u = (await session.execute(select(User).where(User.email == email))).scalars().first()
                if u:
                    m = (await session.execute(select(Membership).where(Membership.user_id == u.id))).scalars().first()
                    assert m is None, "Monday registration must not automatically grant membership"

    asyncio.run(_run())


def test_payment_submission_and_admin_verification_workflow():
    """
    Validates:
    1. User can submit a manual M-Pesa transaction reference (starts in 'pending' status).
    2. Duplicate transaction reference submission is rejected (400).
    3. Non-admin cannot approve or verify payments (403).
    4. Admin approves payment -> membership is activated with computed expiry timestamp -> audit log created.
    5. Newly verified member can immediately access playback.
    """
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as user_client, \
                   AsyncClient(transport=transport, base_url="http://test") as admin_client:

            # 1. Create recording
            async with AsyncSessionLocal() as session:
                rec = Recording(
                    title=f"Proprietary Strategy Session {uuid.uuid4().hex[:4]}",
                    video_source_type="google_drive",
                    drive_file_id="1ProprietaryFileId",
                    access_requirement="members_only",
                    published=True
                )
                session.add(rec)
                await session.commit()
                await session.refresh(rec)
                rec_id = rec.id

            # 2. Register User & Admin
            user_email = f"buyer_{uuid.uuid4().hex[:6]}@example.com"
            admin_email = f"admin_{uuid.uuid4().hex[:6]}@example.com"

            await user_client.post("/auth/register", json={"full_name": "Buyer User", "email": user_email, "password": "Password123!"})
            await admin_client.post("/auth/register", json={"full_name": "Admin User", "email": admin_email, "password": "Password123!"})

            async with AsyncSessionLocal() as session:
                u = (await session.execute(select(User).where(User.email == user_email))).scalars().first()
                u.email_verified = True
                adm = (await session.execute(select(User).where(User.email == admin_email))).scalars().first()
                adm.email_verified = True
                adm.role = "admin"
                await session.commit()

            r_u_login = await user_client.post("/auth/login", json={"email": user_email, "password": "Password123!"})
            assert r_u_login.status_code == 200
            r_adm_login = await admin_client.post("/auth/login", json={"email": admin_email, "password": "Password123!"})
            assert r_adm_login.status_code == 200

            # Check status before payment
            status_res = await user_client.get("/api/membership/my-status")
            assert status_res.status_code == 200
            assert status_res.json()["has_access"] is False

            # 3. Submit payment
            tx_ref = f"MPESA{uuid.uuid4().hex[:8].upper()}"
            sub_res = await user_client.post("/api/membership/submit-payment", json={
                "transaction_reference": tx_ref,
                "payment_method": "M-Pesa",
                "amount": 1500.0,
                "currency": "KES",
                "payer_name": "Buyer User",
                "payer_phone": "+254700000000"
            })
            assert sub_res.status_code == 201, sub_res.text
            sub_data = sub_res.json()
            assert sub_data["status"] == "pending_verification"
            payment_id = sub_data["payment_id"]

            # Duplicate tx_ref should fail
            dup_sub = await user_client.post("/api/membership/submit-payment", json={
                "transaction_reference": tx_ref,
                "amount": 1500.0
            })
            assert dup_sub.status_code == 400

            # 4. User cannot verify their own payment -> 403
            hack_res = await user_client.post(f"/api/admin/memberships/payments/{payment_id}/verify", json={"action": "approved"})
            assert hack_res.status_code == 403

            # 5. Admin verifies and approves payment
            verify_res = await admin_client.post(f"/api/admin/memberships/payments/{payment_id}/verify", json={
                "action": "approved",
                "admin_notes": "Verified against M-Pesa statement."
            })
            assert verify_res.status_code == 200, verify_res.text
            v_data = verify_res.json()
            assert v_data["status"] == "approved"

            # 6. Verify audit log entry
            async with AsyncSessionLocal() as session:
                audit = (await session.execute(
                    select(AuditLog).where(AuditLog.target_id == payment_id, AuditLog.action == "Membership Payment Approved")
                )).scalars().first()
                assert audit is not None
                assert "M-Pesa statement" in audit.details

            # 7. Check user status is now active
            new_status = await user_client.get("/api/membership/my-status")
            assert new_status.status_code == 200
            assert new_status.json()["has_access"] is True

            # 8. Member can now play the protected recording
            playback_res = await user_client.get(f"/api/recordings/{rec_id}/playback")
            assert playback_res.status_code == 200
            assert playback_res.json()["drive_file_id"] == "1ProprietaryFileId"

    asyncio.run(_run())


def test_admin_recordings_crud_and_drive_id_extraction():
    """
    Validates:
    1. Admin can create recording with full Google Drive sharing link, and the system extracts the drive file ID.
    2. Admin can edit recording details and toggle publication status.
    3. Admin can delete recording.
    4. Non-admin cannot perform admin operations on recordings.
    """
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as user_client, \
                   AsyncClient(transport=transport, base_url="http://test") as admin_client:

            admin_email = f"recadmin_{uuid.uuid4().hex[:6]}@example.com"
            user_email = f"recuser_{uuid.uuid4().hex[:6]}@example.com"

            await admin_client.post("/auth/register", json={"full_name": "Rec Admin", "email": admin_email, "password": "Password123!"})
            await user_client.post("/auth/register", json={"full_name": "Rec User", "email": user_email, "password": "Password123!"})

            async with AsyncSessionLocal() as session:
                adm = (await session.execute(select(User).where(User.email == admin_email))).scalars().first()
                adm.email_verified = True
                adm.role = "admin"
                u = (await session.execute(select(User).where(User.email == user_email))).scalars().first()
                u.email_verified = True
                await session.commit()

            r_adm_login = await admin_client.post("/auth/login", json={"email": admin_email, "password": "Password123!"})
            assert r_adm_login.status_code == 200
            r_u_login = await user_client.post("/auth/login", json={"email": user_email, "password": "Password123!"})
            assert r_u_login.status_code == 200

            # Create with a Google Drive sharing URL
            raw_url = "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/view?usp=sharing"
            create_res = await admin_client.post("/api/admin/recordings", json={
                "title": f"Drive ID Extraction Test Session {uuid.uuid4().hex[:4]}",
                "description": "Testing automated regex file ID extraction from Drive URLs.",
                "video_source_type": "google_drive",
                "drive_file_id": raw_url,
                "access_requirement": "members_only",
                "published": True
            })
            assert create_res.status_code == 201, create_res.text
            created_rec = create_res.json()
            rec_id = created_rec["id"]
            assert created_rec["drive_file_id"] == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

            # Non-admin cannot update -> 403
            hack_res = await user_client.put(f"/api/admin/recordings/{rec_id}", json={"title": "Hacked Title"})
            assert hack_res.status_code == 403

            # Admin updates
            update_res = await admin_client.put(f"/api/admin/recordings/{rec_id}", json={
                "title": "Updated Strategy Session",
                "published": False
            })
            assert update_res.status_code == 200
            assert update_res.json()["title"] == "Updated Strategy Session"
            assert update_res.json()["published"] is False

            # Admin deletes
            del_res = await admin_client.delete(f"/api/admin/recordings/{rec_id}")
            assert del_res.status_code == 200

            # Confirm gone
            check_del = await admin_client.put(f"/api/admin/recordings/{rec_id}", json={"title": "Should Fail"})
            assert check_del.status_code == 404

    asyncio.run(_run())
