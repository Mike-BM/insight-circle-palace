"""Regression tests for the security hardening work.

Each test pins down one specific vulnerability that existed before, so it cannot come back
unnoticed: free-membership via simulated payments, forged M-Pesa callbacks, unsigned Stripe
webhooks, weak passwords, cross-site requests, and missing security headers.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.future import select

from app.auth import get_password_hash
from app.database import AsyncSessionLocal
from app.models import (Membership, MpesaTransaction, StripeTransaction, User,
                        utcnow)
from app.schemas import ResetPasswordRequest, UserCreate
from app.security import (is_production, payment_simulation_allowed,
                          safe_redirect_url, validate_password_strength)
from main import app

STRONG_PASSWORD = "Tr1cky-Unique-Passphrase!"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _make_user(role="member", password=STRONG_PASSWORD):
    email = f"sec_{uuid.uuid4().hex[:10]}@example.com"
    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            full_name="Security Tester",
            role=role,
            status="active",
            email_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id, email


# --------------------------------------------------------------------------- environment


def test_production_detection(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    assert is_production() and not payment_simulation_allowed()
    monkeypatch.setenv("APP_ENV", "development")
    assert not is_production() and payment_simulation_allowed()
    # A missing APP_ENV on Vercel must count as production (fail safe)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    assert is_production()


# --------------------------------------------------------------------------- passwords


@pytest.mark.parametrize(
    "bad", ["short1", "123456789", "password123", "Password", "aaaaaaaaaaaa", "ADMIN123"]
)
def test_weak_passwords_rejected(bad):
    with pytest.raises(ValueError):
        validate_password_strength(bad)


def test_strong_password_accepted_and_schemas_enforce_policy():
    assert validate_password_strength(STRONG_PASSWORD) == STRONG_PASSWORD
    with pytest.raises(ValidationError):
        UserCreate(email="a@example.com", password="password123", full_name="A")
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token="t", new_password="12345678")
    UserCreate(email="a@example.com", password=STRONG_PASSWORD, full_name="A")


def test_register_endpoint_rejects_weak_password():
    async def _run():
        async with _client() as c:
            r = await c.post(
                "/auth/register",
                json={"email": f"w_{uuid.uuid4().hex[:6]}@example.com", "password": "password123", "full_name": "W"},
            )
            assert r.status_code == 422

    asyncio.run(_run())


# --------------------------------------------------------------------------- headers / CSRF


def test_security_headers_present():
    async def _run():
        async with _client() as c:
            r = await c.get("/health")
            h = r.headers
            assert h["x-content-type-options"] == "nosniff"
            assert h["x-frame-options"] == "DENY"
            assert h["referrer-policy"] == "strict-origin-when-cross-origin"
            assert "camera=()" in h["permissions-policy"]
            assert "frame-ancestors 'none'" in h["content-security-policy"]
            assert "content-security-policy-report-only" in h
            assert "max-age" in h["strict-transport-security"]

    asyncio.run(_run())


def test_csrf_blocks_cross_site_post_with_session_cookie():
    async def _run():
        async with _client() as c:
            c.cookies.set("insight_session", "anything")
            r = await c.post("/auth/logout", headers={"Origin": "https://evil.example"})
            assert r.status_code == 403
            # same-site request is allowed through
            ok = await c.post("/auth/logout", headers={"Origin": "https://insightcirclepalace.com"})
            assert ok.status_code != 403

    asyncio.run(_run())


# --------------------------------------------------------------------------- M-Pesa


def test_simulate_callback_endpoint_is_admin_only_and_dead_in_production(monkeypatch):
    async def _run():
        member_id, member_email = await _make_user("member")
        admin_id, admin_email = await _make_user("admin")

        async with _client() as c_member, _client() as c_admin:
            assert (await c_member.post("/auth/login", json={"email": member_email, "password": STRONG_PASSWORD})).status_code == 200
            assert (await c_admin.post("/auth/login", json={"email": admin_email, "password": STRONG_PASSWORD})).status_code == 200
            body = {"checkout_request_id": "ws_CO_x", "success": True}

            # A normal member can never call it (previously ANY logged-in user could).
            r = await c_member.post("/api/payments/mpesa/simulate-callback", json=body)
            assert r.status_code == 403

            # Even an admin cannot use it in production.
            monkeypatch.setenv("APP_ENV", "production")
            r = await c_admin.post("/api/payments/mpesa/simulate-callback", json=body)
            assert r.status_code == 404

    asyncio.run(_run())


def test_forged_mpesa_success_callback_does_not_grant_membership_in_production(monkeypatch):
    """Daraja callbacks are unsigned: a forged 'success' must not activate anything."""

    async def _run():
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("MPESA_CONSUMER_KEY", raising=False)
        monkeypatch.delenv("MPESA_CONSUMER_SECRET", raising=False)
        monkeypatch.delenv("MPESA_CALLBACK_TOKEN", raising=False)

        user_id, _ = await _make_user("member")
        checkout_id = f"ws_CO_FORGED_{uuid.uuid4().hex[:10]}"
        async with AsyncSessionLocal() as session:
            session.add(
                MpesaTransaction(
                    user_id=user_id,
                    phone_number="254712345678",
                    amount=250.0,
                    checkout_request_id=checkout_id,
                    status="initiated",
                    purpose="membership",
                )
            )
            await session.commit()

        forged = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "x",
                    "CheckoutRequestID": checkout_id,
                    "ResultCode": 0,
                    "ResultDesc": "ok",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 250},
                            {"Name": "MpesaReceiptNumber", "Value": "FAKE123456"},
                        ]
                    },
                }
            }
        }
        async with _client() as c:
            r = await c.post("/api/payments/mpesa/callback", json=forged)
            assert r.status_code == 200  # Safaricom-style acknowledgement

        async with AsyncSessionLocal() as session:
            tx = (await session.execute(select(MpesaTransaction).where(MpesaTransaction.checkout_request_id == checkout_id))).scalars().first()
            assert tx.status == "initiated", "forged callback must not mark the payment successful"
            mems = (await session.execute(select(Membership).where(Membership.user_id == user_id))).scalars().all()
            assert mems == []

    asyncio.run(_run())


def test_mpesa_callback_requires_secret_token_when_configured(monkeypatch):
    async def _run():
        monkeypatch.setenv("MPESA_CALLBACK_TOKEN", "s3cret-token-value")
        payload = {"Body": {"stkCallback": {"CheckoutRequestID": "does-not-exist", "ResultCode": 1032}}}
        async with _client() as c:
            assert (await c.post("/api/payments/mpesa/callback", json=payload)).status_code == 403
            assert (await c.post("/api/payments/mpesa/callback?token=wrong", json=payload)).status_code == 403
            assert (await c.post("/api/payments/mpesa/callback?token=s3cret-token-value", json=payload)).status_code == 200

    asyncio.run(_run())


# --------------------------------------------------------------------------- Stripe


def test_simulated_stripe_session_is_never_honoured_in_production(monkeypatch):
    from app.services.stripe_service import verify_and_fulfill_session

    async def _run():
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

        user_id, _ = await _make_user("member")
        session_id = f"cs_test_sim_{uuid.uuid4().hex[:12]}"
        async with AsyncSessionLocal() as session:
            session.add(
                StripeTransaction(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    session_id=session_id,
                    amount=2.5,
                    currency="USD",
                    status="initiated",
                    purpose="membership",
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
            await session.commit()

        async with AsyncSessionLocal() as session:
            result = await verify_and_fulfill_session(session_id, session)
            assert result["success"] is False

        async with AsyncSessionLocal() as session:
            mems = (await session.execute(select(Membership).where(Membership.user_id == user_id))).scalars().all()
            assert mems == [], "a simulated session must never create a membership in production"

    asyncio.run(_run())


def test_unknown_stripe_session_is_rejected(monkeypatch):
    from app.services.stripe_service import verify_and_fulfill_session

    async def _run():
        monkeypatch.setenv("APP_ENV", "development")
        async with AsyncSessionLocal() as session:
            result = await verify_and_fulfill_session("cs_test_sim_never_created", session)
            assert result["success"] is False
            assert result["status"] == "unknown_session"

    asyncio.run(_run())


def test_stripe_webhook_refused_without_secret_in_production(monkeypatch):
    async def _run():
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        async with _client() as c:
            r = await c.post("/api/payments/stripe/webhook", content=b"{}", headers={"Content-Type": "application/json"})
            assert r.status_code == 503

    asyncio.run(_run())


def test_stripe_webhook_rejects_bad_signature_when_secret_set(monkeypatch):
    async def _run():
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
        async with _client() as c:
            r = await c.post(
                "/api/payments/stripe/webhook",
                content=b'{"type":"checkout.session.completed"}',
                headers={"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=deadbeef"},
            )
            assert r.status_code == 400

    asyncio.run(_run())


def test_payment_redirect_urls_limited_to_own_domain():
    base = "https://insightcirclepalace.com"
    default = f"{base}/static/recordings.html"
    assert safe_redirect_url("https://evil.example/phish", default, base) == default
    assert safe_redirect_url("javascript:alert(1)", default, base) == default
    assert safe_redirect_url("//evil.example/x", default, base) == default
    assert safe_redirect_url(None, default, base) == default
    assert safe_redirect_url(f"{base}/static/merchandise.html?ok=1", default, base).startswith(base)
    assert safe_redirect_url("https://www.insightcirclepalace.com/x", default, base).startswith("https://www.")


# --------------------------------------------------------------------------- memberships


def test_expired_active_membership_has_no_access():
    from app.services.membership import check_user_membership

    async def _run():
        user_id, _ = await _make_user("member")
        async with AsyncSessionLocal() as session:
            session.add(
                Membership(
                    user_id=user_id,
                    status="active",
                    fee_paid=250.0,
                    currency="KES",
                    activated_at=datetime.now(timezone.utc) - timedelta(days=90),
                    expires_at=datetime.now(timezone.utc) - timedelta(days=1),
                )
            )
            await session.commit()
        async with AsyncSessionLocal() as session:
            user = (await session.execute(select(User).where(User.id == user_id))).scalars().first()
            status = await check_user_membership(user, session)
            assert status["has_access"] is False
            assert status["status"] == "expired"

    asyncio.run(_run())


# --------------------------------------------------------------------------- login


def test_login_unknown_and_wrong_password_look_identical():
    async def _run():
        _, email = await _make_user("member")
        async with _client() as c:
            wrong = await c.post("/auth/login", json={"email": email, "password": "Definitely-Wrong-1"})
            unknown = await c.post("/auth/login", json={"email": "nobody_here@example.com", "password": "Definitely-Wrong-1"})
            assert wrong.status_code == unknown.status_code == 401
            assert wrong.json() == unknown.json()

    asyncio.run(_run())


def test_no_hardcoded_admin_password_backdoor():
    """An admin whose password is X must not be reachable with the old 'admin123' defaults."""

    async def _run():
        admin_id, admin_email = await _make_user("super_admin", password="Admin123!")
        async with _client() as c:
            ok = await c.post("/auth/login", json={"email": admin_email, "password": "Admin123!"})
            assert ok.status_code == 200  # their real password works
            bad = await c.post("/auth/login", json={"email": admin_email, "password": "admin123"})
            assert bad.status_code == 401  # the old hardcoded alternative must not

    asyncio.run(_run())
