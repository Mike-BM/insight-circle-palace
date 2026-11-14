import pytest
import uuid
from datetime import datetime, timezone

from app.models import (
    Base,
    MerchandiseOrder,
    Membership,
    MpesaTransaction,
    StripeTransaction,
    User,
    utcnow,
)
from app.services.mpesa import (
    initiate_stk_push,
    normalize_phone_number,
    process_stk_callback,
    simulate_mock_callback,
)
from app.services.stripe_service import (
    convert_kes_to_usd,
    create_membership_checkout_session,
    create_merchandise_checkout_session,
    get_stripe_config,
    verify_and_fulfill_session,
    verify_stripe_webhook_signature,
)


def test_stripe_config_and_currency_conversion():
    config = get_stripe_config()
    assert "publishable_key" in config
    assert config["membership_price_usd"] == 2.50
    assert config["currency"] == "USD"

    # Test KES to USD conversion
    usd_tumbler = convert_kes_to_usd(1100.0)  # 1100 / 130 ~ 8.46
    assert usd_tumbler > 8.0 and usd_tumbler < 9.0

    usd_min = convert_kes_to_usd(50.0)
    assert usd_min >= 1.0  # Minimum 1 USD floor


def test_stripe_signature_verification():
    import hashlib
    import hmac
    import time

    secret = "whsec_test_secret_key"
    payload = b'{"type": "checkout.session.completed", "id": "evt_123"}'
    ts = int(time.time())

    signed_payload = f"{ts}.".encode("utf-8") + payload
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    sig_header = f"t={ts},v1={sig}"

    # Valid signature
    assert verify_stripe_webhook_signature(payload, sig_header, secret) is True

    # Invalid signature
    assert verify_stripe_webhook_signature(payload, f"t={ts},v1=bad_sig", secret) is False

    # Expired signature
    old_ts = ts - 400
    old_signed = f"{old_ts}.".encode("utf-8") + payload
    old_sig = hmac.new(secret.encode("utf-8"), old_signed, hashlib.sha256).hexdigest()
    assert verify_stripe_webhook_signature(payload, f"t={old_ts},v1={old_sig}", secret, tolerance_seconds=300) is False


@pytest.mark.asyncio
async def test_stripe_and_mpesa_merchandise_flow():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    # Use in-memory SQLite for isolated async testing
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with TestSession() as session:
        # Create test user
        user = User(
            id=str(uuid.uuid4()),
            email=f"learner_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="x-not-a-real-hash",
            full_name="Test Learner",
            role="member",
            status="active",
            created_at=utcnow(),
        )
        session.add(user)

        # Create test merchandise order
        order_number = f"ICP-ORD-TEST-{uuid.uuid4().hex[:4].upper()}"
        order = MerchandiseOrder(
            id=str(uuid.uuid4()),
            order_number=order_number,
            full_name="Test Buyer",
            phone="254712345678",
            email="buyer@example.com",
            product_id="hoodie",
            product_name="Luxury ICP Hoodie",
            quantity=1,
            unit_price=2500.0,
            total_price=2500.0,
            currency="KES",
            fulfillment_type="direct",
            status="pending",
            payment_status="unpaid",
            payment_method="mpesa",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(order)
        await session.commit()

        # 1. Test Stripe Membership Checkout (Simulation Mode)
        checkout_res = await create_membership_checkout_session(user, session)
        assert checkout_res["success"] is True
        assert checkout_res["session_id"].startswith("cs_test_sim_")
        session_id = checkout_res["session_id"]

        # Verify and fulfill Stripe membership session
        fulfill_res = await verify_and_fulfill_session(session_id, session)
        assert fulfill_res["success"] is True
        assert fulfill_res["status"] == "completed"

        # Check membership is now active
        from sqlalchemy import select
        mem_res = await session.execute(select(Membership).where(Membership.user_id == user.id))
        mem = mem_res.scalars().first()
        assert mem is not None
        assert mem.status == "active"
        assert mem.currency == "USD"

        # 2. Test M-Pesa STK Push for Merchandise Order
        mpesa_res = await initiate_stk_push(
            user=user,
            phone_number="0712345678",
            db=session,
            amount=order.total_price,
            purpose="merchandise",
            order_number=order.order_number,
        )
        assert mpesa_res["success"] is True
        assert mpesa_res["amount"] == 2500.0
        checkout_req_id = mpesa_res["checkout_request_id"]

        # Simulate M-Pesa callback for merchandise order
        sim_cb = await simulate_mock_callback(checkout_req_id, session, success=True, mock_receipt="QWE123TEST")
        assert sim_cb["ResultCode"] == 0

        # Verify order is now marked paid
        await session.refresh(order)
        assert order.payment_status == "paid"
        assert order.payment_reference == "QWE123TEST"
        assert order.payment_method == "mpesa"
        assert order.status == "confirmed"

    await test_engine.dispose()

