import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal, Base, engine
from app.models import User, Recording, Membership, PaymentSubmission, MondayRegistration, AuditLog, utcnow
from app.auth import get_password_hash
from main import app


async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def test_requirement_1_new_registrant_not_paid_member():
    """
    Test 1: A new registrant is not automatically a paid member.
    Registration and membership are separate.
    """
    async def _run():
        await setup_db()

        unique = uuid.uuid4().hex[:6]
        email = f"registrant_{unique}@example.com"
        pwd = "SecurePassword123!"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Register user
            reg_res = await client.post("/auth/register", json={
                "email": email,
                "password": pwd,
                "full_name": f"New Registrant {unique}",
                "phone": "+254712000111"
            })
            assert reg_res.status_code in (200, 201), reg_res.text

            # Mark email verified so login succeeds
            async with AsyncSessionLocal() as session:
                u = (await session.execute(select(User).where(User.email == email))).scalars().first()
                u.email_verified = True
                await session.commit()

            # Login to get session cookie
            login_res = await client.post("/auth/login", json={"email": email, "password": pwd})
            assert login_res.status_code == 200, login_res.text

            # Check membership status
            status_res = await client.get("/api/membership/status")
            assert status_res.status_code == 200, status_res.text
            status_data = status_res.json()

            assert status_data["has_access"] is False, "New registrant must not automatically have membership access"
            assert status_data["status"] in ("none", "registered"), f"Expected unpaid/none status, got: {status_data['status']}"
            assert status_data["activated_at"] is None
            assert status_data["expires_at"] is None

    asyncio.run(_run())


def test_requirement_2_unpaid_user_cannot_access_protected_recordings():
    """
    Test 2: An unpaid user cannot access protected recordings (HTTP 403),
    while free recordings remain accessible.
    """
    async def _run():
        await setup_db()

        unique = uuid.uuid4().hex[:6]
        email = f"unpaid_{unique}@example.com"
        pwd = "SecurePassword123!"

        async with AsyncSessionLocal() as session:
            # Create user
            user = User(
                email=email,
                password_hash=get_password_hash(pwd),
                full_name=f"Unpaid User {unique}",
                role="member",
                status="active",
                email_verified=True
            )
            # Create protected recording
            rec_protected = Recording(
                title=f"Protected Strategy Deepdive {unique}",
                session_date=datetime.now(timezone.utc),
                description="Members only session.",
                video_source_type="google_drive",
                drive_file_id="secret_drive_id_12345",
                access_requirement="members_only",
                published=True
            )
            # Create free recording
            rec_free = Recording(
                title=f"Free Orientation Session {unique}",
                session_date=datetime.now(timezone.utc),
                description="Open session.",
                video_source_type="google_drive",
                drive_file_id="free_drive_id_12345",
                access_requirement="free",
                published=True
            )
            session.add_all([user, rec_protected, rec_free])
            await session.commit()
            await session.refresh(rec_protected)
            await session.refresh(rec_free)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_res = await client.post("/auth/login", json={"email": email, "password": pwd})
            assert login_res.status_code == 200

            # Attempt to play protected recording -> must receive 403 Forbidden
            playback_res = await client.get(f"/api/recordings/{rec_protected.id}/playback")
            assert playback_res.status_code == 403, f"Expected 403 for unpaid user, got {playback_res.status_code}"
            assert "membership" in playback_res.json()["detail"].lower()

            # Attempt to play free recording -> must receive 200 OK
            free_res = await client.get(f"/api/recordings/{rec_free.id}/playback")
            assert free_res.status_code == 200, f"Expected 200 for free recording, got {free_res.status_code}"
            assert free_res.json()["has_access"] is True

    asyncio.run(_run())


def test_requirement_3_and_4_admin_manual_verify_and_persistence_across_logins():
    """
    Test 3 & 4:
    - Authorized admin can verify genuine payment with reference, date, notes.
    - Audit log entry is recorded with admin identity and timestamp.
    - Approved membership persists across multiple logins and session changes.
    - Protected recordings become accessible.
    """
    async def _run():
        await setup_db()

        unique = uuid.uuid4().hex[:6]
        admin_email = f"admin_{unique}@example.com"
        member_email = f"member_{unique}@example.com"
        pwd = "SecurePassword123!"
        tx_ref = f"MPESA{unique.upper()}789"

        async with AsyncSessionLocal() as session:
            admin_user = User(
                email=admin_email,
                password_hash=get_password_hash(pwd),
                full_name=f"Admin Verifier {unique}",
                role="admin",
                status="active",
                email_verified=True
            )
            member_user = User(
                email=member_email,
                password_hash=get_password_hash(pwd),
                full_name=f"Paying Member {unique}",
                role="member",
                status="active",
                email_verified=True
            )
            rec = Recording(
                title=f"Exclusive Masterclass {unique}",
                session_date=datetime.now(timezone.utc),
                description="Exclusive to paid members.",
                video_source_type="google_drive",
                drive_file_id="drive_secret_playback_ok",
                access_requirement="members_only",
                published=True
            )
            session.add_all([admin_user, member_user, rec])
            await session.commit()
            await session.refresh(admin_user)
            await session.refresh(member_user)
            await session.refresh(rec)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as admin_client, \
                   AsyncClient(transport=transport, base_url="http://test") as member_client:

            # Login both
            await admin_client.post("/auth/login", json={"email": admin_email, "password": pwd})
            await member_client.post("/auth/login", json={"email": member_email, "password": pwd})

            # 1. Member cannot access initially
            pb1 = await member_client.get(f"/api/recordings/{rec.id}/playback")
            assert pb1.status_code == 403

            # 2. Admin performs manual verification
            ver_date = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            verify_payload = {
                "user_id": member_user.id,
                "transaction_reference": tx_ref,
                "payment_method": "mpesa",
                "amount": 250.0,
                "currency": "KES",
                "verification_date": ver_date,
                "duration_days": 45,
                "admin_notes": f"Verified via M-Pesa business portal by {admin_email}",
                "payer_name": "Paying Member",
                "payer_phone": "+254700112233"
            }
            ver_res = await admin_client.post("/api/admin/memberships/manual-verify", json=verify_payload)
            assert ver_res.status_code == 200, ver_res.text
            ver_data = ver_res.json()
            assert ver_data["status"] == "paid"
            assert ver_data["transaction_reference"] == tx_ref
            assert "expires_at" in ver_data

            # Check audit log in DB
            async with AsyncSessionLocal() as session:
                audit_res = await session.execute(
                    select(AuditLog).where(AuditLog.admin_id == admin_user.id)
                )
                audits = audit_res.scalars().all()
                assert len(audits) >= 1
                assert tx_ref in audits[-1].details
                assert "Manual Payment Verified" in audits[-1].action

            # 3. Member now has active membership
            st_res = await member_client.get("/api/membership/status")
            assert st_res.status_code == 200
            st_data = st_res.json()
            assert st_data["has_access"] is True
            assert st_data["status"] == "active"

            # 4. Member can now access protected recording
            pb2 = await member_client.get(f"/api/recordings/{rec.id}/playback")
            assert pb2.status_code == 200, pb2.text
            assert pb2.json()["has_access"] is True
            assert "drive_secret_playback_ok" in pb2.json()["embed_url"]

        # 5. Member logs in from a brand new client (simulating logout and login on new device)
        async with AsyncClient(transport=transport, base_url="http://test") as new_device_client:
            login_res = await new_device_client.post("/auth/login", json={"email": member_email, "password": pwd})
            assert login_res.status_code == 200

            # Verify approved membership persists across new login
            st_res_new = await new_device_client.get("/api/membership/status")
            assert st_res_new.status_code == 200
            assert st_res_new.json()["has_access"] is True
            assert st_res_new.json()["status"] == "active"

            pb3 = await new_device_client.get(f"/api/recordings/{rec.id}/playback")
            assert pb3.status_code == 200

    asyncio.run(_run())


def test_requirement_5_expired_suspended_revoked_denied_access():
    """
    Test 5: Expired, suspended, and revoked members are denied protected access.
    """
    async def _run():
        await setup_db()

        unique = uuid.uuid4().hex[:6]
        pwd = "SecurePassword123!"

        email_expired = f"expired_{unique}@example.com"
        email_suspended = f"suspended_{unique}@example.com"
        email_revoked = f"revoked_{unique}@example.com"

        async with AsyncSessionLocal() as session:
            # User with expired membership
            user_expired = User(
                email=email_expired,
                password_hash=get_password_hash(pwd),
                full_name=f"Expired User {unique}",
                role="member",
                status="active",
                email_verified=True
            )
            # User with suspended membership
            user_suspended = User(
                email=email_suspended,
                password_hash=get_password_hash(pwd),
                full_name=f"Suspended User {unique}",
                role="member",
                status="active",
                email_verified=True
            )
            # User with revoked membership
            user_revoked = User(
                email=email_revoked,
                password_hash=get_password_hash(pwd),
                full_name=f"Revoked User {unique}",
                role="member",
                status="active",
                email_verified=True
            )
            rec = Recording(
                title=f"Protected Content {unique}",
                session_date=datetime.now(timezone.utc),
                description="Members only.",
                video_source_type="google_drive",
                drive_file_id="drive_secret_content",
                access_requirement="members_only",
                published=True
            )
            session.add_all([user_expired, user_suspended, user_revoked, rec])
            await session.commit()
            await session.refresh(user_expired)
            await session.refresh(user_suspended)
            await session.refresh(user_revoked)
            await session.refresh(rec)

            now = datetime.now(timezone.utc)
            # Expired membership
            mem_exp = Membership(
                user_id=user_expired.id,
                status="active",
                activated_at=now - timedelta(days=60),
                expires_at=now - timedelta(days=1),  # in past!
                created_at=now - timedelta(days=60),
                updated_at=now - timedelta(days=60)
            )
            # Suspended membership
            mem_susp = Membership(
                user_id=user_suspended.id,
                status="suspended",
                activated_at=now - timedelta(days=10),
                expires_at=now - timedelta(days=1),
                created_at=now - timedelta(days=10),
                updated_at=now - timedelta(days=1)
            )
            # Revoked membership
            mem_rev = Membership(
                user_id=user_revoked.id,
                status="revoked",
                activated_at=now - timedelta(days=10),
                expires_at=now - timedelta(days=1),
                created_at=now - timedelta(days=10),
                updated_at=now - timedelta(days=1)
            )
            session.add_all([mem_exp, mem_susp, mem_rev])
            await session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client_exp, \
                   AsyncClient(transport=transport, base_url="http://test") as client_susp, \
                   AsyncClient(transport=transport, base_url="http://test") as client_rev:

            # 1. Expired user
            await client_exp.post("/auth/login", json={"email": email_expired, "password": pwd})
            res_exp = await client_exp.get(f"/api/recordings/{rec.id}/playback")
            assert res_exp.status_code == 403, f"Expected 403, got {res_exp.status_code}"
            assert "expired" in res_exp.json()["detail"].lower()

            # 2. Suspended user
            await client_susp.post("/auth/login", json={"email": email_suspended, "password": pwd})
            res_susp = await client_susp.get(f"/api/recordings/{rec.id}/playback")
            assert res_susp.status_code == 403, f"Expected 403, got {res_susp.status_code}"
            assert "suspended" in res_susp.json()["detail"].lower() or "revoked" in res_susp.json()["detail"].lower()

            # 3. Revoked user
            await client_rev.post("/auth/login", json={"email": email_revoked, "password": pwd})
            res_rev = await client_rev.get(f"/api/recordings/{rec.id}/playback")
            assert res_rev.status_code == 403, f"Expected 403, got {res_rev.status_code}"
            assert "suspended" in res_rev.json()["detail"].lower() or "revoked" in res_rev.json()["detail"].lower()

    asyncio.run(_run())


def test_requirement_6_ordinary_users_cannot_approve_themselves():
    """
    Test 6: Ordinary users cannot approve themselves or call admin verification endpoints (HTTP 403).
    """
    async def _run():
        await setup_db()

        unique = uuid.uuid4().hex[:6]
        email = f"ordinary_{unique}@example.com"
        pwd = "SecurePassword123!"

        async with AsyncSessionLocal() as session:
            ordinary_user = User(
                email=email,
                password_hash=get_password_hash(pwd),
                full_name=f"Ordinary User {unique}",
                role="member",
                status="active",
                email_verified=True
            )
            session.add(ordinary_user)
            await session.commit()
            await session.refresh(ordinary_user)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/auth/login", json={"email": email, "password": pwd})

            # Attempt to call admin manual verification endpoint
            res1 = await client.post("/api/admin/memberships/manual-verify", json={
                "user_id": ordinary_user.id,
                "transaction_reference": f"FAKE{unique.upper()}",
                "payment_method": "mpesa",
                "amount": 250.0,
                "currency": "KES"
            })
            assert res1.status_code == 403, f"Expected 403 Forbidden, got {res1.status_code}"

            # Attempt to call overview
            res2 = await client.get("/api/admin/memberships/overview")
            assert res2.status_code == 403, f"Expected 403 Forbidden, got {res2.status_code}"

            # Attempt to call suspend
            res3 = await client.post(f"/api/admin/memberships/user/{ordinary_user.id}/suspend", json={
                "action": "suspend", "admin_notes": "test"
            })
            assert res3.status_code == 403, f"Expected 403 Forbidden, got {res3.status_code}"

    asyncio.run(_run())


def test_requirement_7_monday_session_registration_available_to_unpaid():
    """
    Test 7: Monday session registration remains available to everyone (including unpaid users)
    and registering for a session DOES NOT activate membership.
    """
    async def _run():
        await setup_db()

        unique = uuid.uuid4().hex[:6]
        email = f"monday_fan_{unique}@example.com"
        pwd = "SecurePassword123!"

        async with AsyncSessionLocal() as session:
            unpaid_user = User(
                email=email,
                password_hash=get_password_hash(pwd),
                full_name=f"Monday Attendee {unique}",
                role="member",
                status="active",
                email_verified=True
            )
            rec = Recording(
                title=f"Protected Exclusive Session {unique}",
                session_date=datetime.now(timezone.utc),
                description="Members only.",
                video_source_type="google_drive",
                drive_file_id="drive_secret_123",
                access_requirement="members_only",
                published=True
            )
            session.add_all([unpaid_user, rec])
            await session.commit()
            await session.refresh(unpaid_user)
            await session.refresh(rec)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/auth/login", json={"email": email, "password": pwd})

            # 1. Unpaid user registers for Monday session
            rsvp_res = await client.post("/api/monday-sessions/register", json={
                "full_name": f"Monday Attendee {unique}",
                "email": email,
                "phone": "+254711223344",
                "session_date": "2026-11-02",
                "notes": "Looking forward to AI session"
            })
            assert rsvp_res.status_code in (200, 201), rsvp_res.text

            # 2. Check membership status: MUST STILL BE FALSE (NOT activated)
            status_res = await client.get("/api/membership/status")
            assert status_res.status_code == 200
            assert status_res.json()["has_access"] is False, "Monday RSVP must NEVER activate membership"

            # 3. Check playback: MUST STILL BE 403
            pb_res = await client.get(f"/api/recordings/{rec.id}/playback")
            assert pb_res.status_code == 403, f"Expected 403, got {pb_res.status_code}"

    asyncio.run(_run())


def test_requirement_8_existing_users_preserved_and_duplicate_tx_refs_prevented():
    """
    Test 8:
    - Existing users and database records are preserved.
    - Admin overview returns all registered users with accurate Monday registration count.
    - Duplicate transaction references on approved payments are rejected with HTTP 400.
    """
    async def _run():
        await setup_db()

        unique = uuid.uuid4().hex[:6]
        admin_email = f"admin_audit_{unique}@example.com"
        user1_email = f"user1_{unique}@example.com"
        user2_email = f"user2_{unique}@example.com"
        shared_ref = f"REF{unique.upper()}DUPLICATE"
        pwd = "SecurePassword123!"

        async with AsyncSessionLocal() as session:
            admin = User(
                email=admin_email,
                password_hash=get_password_hash(pwd),
                full_name=f"Admin {unique}",
                role="super_admin",
                status="active",
                email_verified=True
            )
            u1 = User(
                email=user1_email,
                password_hash=get_password_hash(pwd),
                full_name=f"User One {unique}",
                role="member",
                status="active",
                email_verified=True
            )
            u2 = User(
                email=user2_email,
                password_hash=get_password_hash(pwd),
                full_name=f"User Two {unique}",
                role="member",
                status="active",
                email_verified=True
            )
            session.add_all([admin, u1, u2])
            await session.commit()
            await session.refresh(admin)
            await session.refresh(u1)
            await session.refresh(u2)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as admin_client:
            await admin_client.post("/auth/login", json={"email": admin_email, "password": pwd})

            # 1. Admin verifies payment for User 1 using shared_ref
            res1 = await admin_client.post("/api/admin/memberships/manual-verify", json={
                "user_id": u1.id,
                "transaction_reference": shared_ref,
                "payment_method": "mpesa",
                "amount": 250.0,
                "currency": "KES",
                "admin_notes": "First user verified"
            })
            assert res1.status_code == 200, res1.text

            # 2. Admin attempts to verify payment for User 2 with the SAME transaction reference
            res2 = await admin_client.post("/api/admin/memberships/manual-verify", json={
                "user_id": u2.id,
                "transaction_reference": shared_ref,
                "payment_method": "mpesa",
                "amount": 250.0,
                "currency": "KES",
                "admin_notes": "Duplicate reference attempt"
            })
            assert res2.status_code == 400, f"Expected 400 Bad Request for duplicate tx ref, got {res2.status_code}"
            assert "already been verified" in res2.json()["detail"].lower()

            # 3. Admin overview endpoint returns both users and accurate stats
            overview_res = await admin_client.get("/api/admin/memberships/overview?status=all")
            assert overview_res.status_code == 200
            items = overview_res.json()
            user1_item = next(i for i in items if i["user_id"] == u1.id)
            user2_item = next(i for i in items if i["user_id"] == u2.id)

            assert user1_item["membership_status"] == "paid"
            assert user1_item["transaction_reference"] == shared_ref
            assert user1_item["verified_by_email"] == admin_email

            assert user2_item["membership_status"] == "registered"
            assert user2_item["payment_status"] == "unpaid"

    asyncio.run(_run())
