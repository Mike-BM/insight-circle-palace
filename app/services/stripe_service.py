import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import (
    AuditLog,
    Membership,
    MerchandiseOrder,
    PaymentSubmission,
    StripeTransaction,
    User,
    utcnow,
)
from app.services.membership import check_user_membership

logger = logging.getLogger("stripe_service")

# --- Configuration Constants ---
STRIPE_API_BASE = "https://api.stripe.com/v1"
DEFAULT_MEMBERSHIP_PRICE_USD = 2.50
DEFAULT_KES_TO_USD_RATE = 130.0  # Approx 1 USD = 130 KES


def get_stripe_secret_key() -> str:
    return os.getenv("STRIPE_SECRET_KEY", "").strip()


def get_stripe_publishable_key() -> str:
    return os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()


def get_stripe_webhook_secret() -> str:
    return os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()


def get_base_url() -> str:
    return os.getenv("BASE_URL", "https://insightcirclepalace.com").rstrip("/")


def get_stripe_config() -> Dict[str, Any]:
    secret = get_stripe_secret_key()
    pub = get_stripe_publishable_key()
    is_configured = bool(secret and not secret.startswith("sk_test_placeholder"))
    is_live = secret.startswith("sk_live_")

    membership_usd = float(os.getenv("STRIPE_MEMBERSHIP_PRICE_USD", str(DEFAULT_MEMBERSHIP_PRICE_USD)))
    kes_usd_rate = float(os.getenv("KES_TO_USD_RATE", str(DEFAULT_KES_TO_USD_RATE)))

    return {
        "is_configured": is_configured,
        "is_live": is_live,
        "publishable_key": pub,
        "membership_price_usd": membership_usd,
        "kes_to_usd_rate": kes_usd_rate,
        "currency": "USD",
    }


def convert_kes_to_usd(amount_kes: float) -> float:
    rate = float(os.getenv("KES_TO_USD_RATE", str(DEFAULT_KES_TO_USD_RATE)))
    usd = round(amount_kes / rate, 2)
    return max(usd, 1.0)  # Minimum 1 USD for Stripe charges


async def create_membership_checkout_session(
    user: User,
    db: AsyncSession,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a Stripe Checkout Session for Insight Circle Palace Membership.
    Supports both live Stripe API and local simulation mode.
    """
    # 1. Check if user already has an active membership
    mem_status = await check_user_membership(user, db)
    if mem_status.get("has_access") and mem_status.get("status") == "active":
        return {
            "success": True,
            "status": "already_active",
            "already_active": True,
            "message": "Your membership is already active! You do not need to pay again.",
        }

    base_url = get_base_url()
    final_success_url = success_url or f"{base_url}/static/recordings.html?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    final_cancel_url = cancel_url or f"{base_url}/static/recordings.html?payment=cancelled"

    price_usd = float(os.getenv("STRIPE_MEMBERSHIP_PRICE_USD", str(DEFAULT_MEMBERSHIP_PRICE_USD)))
    unit_amount_cents = int(round(price_usd * 100))

    secret_key = get_stripe_secret_key()
    session_id = None
    checkout_url = None

    if secret_key and not secret_key.startswith("sk_test_placeholder"):
        # Real Stripe API Call via HTTPX
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        form_data = {
            "mode": "payment",
            "success_url": final_success_url,
            "cancel_url": final_cancel_url,
            "client_reference_id": user.id,
            "customer_email": user.email,
            "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][unit_amount]": str(unit_amount_cents),
            "line_items[0][price_data][product_data][name]": "Insight Circle Palace - Lifetime Membership",
            "line_items[0][price_data][product_data][description]": "Full lifetime access to all past masterclasses, recordings, and executive community features.",
            "metadata[user_id]": user.id,
            "metadata[purpose]": "membership",
            "payment_method_types[0]": "card",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{STRIPE_API_BASE}/checkout/sessions",
                    data=form_data,
                    headers=headers,
                )
                data = resp.json()
                if resp.status_code == 200:
                    session_id = data.get("id")
                    checkout_url = data.get("url")
                else:
                    err_msg = data.get("error", {}).get("message", "Stripe API error")
                    logger.error(f"Stripe error creating session: {err_msg}")
                    raise RuntimeError(f"Stripe error: {err_msg}")
        except httpx.RequestError as e:
            logger.error(f"Network error contacting Stripe: {e}")
            raise RuntimeError("Unable to connect to Stripe payment gateway. Please try again.")
    else:
        # Development / Simulation mode
        token = uuid.uuid4().hex[:16]
        session_id = f"cs_test_sim_{token}"
        checkout_url = final_success_url.replace("{CHECKOUT_SESSION_ID}", session_id) + "&simulated=true"
        logger.info(f"Stripe running in simulation mode. Generated session: {session_id}")

    # Record StripeTransaction in DB
    tx = StripeTransaction(
        id=str(uuid.uuid4()),
        user_id=user.id,
        order_number=None,
        session_id=session_id,
        amount=price_usd,
        currency="USD",
        status="initiated",
        purpose="membership",
        customer_email=user.email,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    return {
        "success": True,
        "session_id": session_id,
        "checkout_url": checkout_url,
        "amount_usd": price_usd,
        "currency": "USD",
        "purpose": "membership",
    }


async def create_merchandise_checkout_session(
    order: MerchandiseOrder,
    db: AsyncSession,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a Stripe Checkout Session for a Merchandise Order.
    Calculates USD equivalent for total price and passes order details.
    """
    if order.payment_status == "paid":
        return {
            "success": True,
            "status": "already_paid",
            "already_paid": True,
            "message": f"Order {order.order_number} is already paid.",
        }

    base_url = get_base_url()
    final_success_url = success_url or f"{base_url}/static/merchandise.html?order={order.order_number}&status=paid&session_id={{CHECKOUT_SESSION_ID}}"
    final_cancel_url = cancel_url or f"{base_url}/static/merchandise.html?order={order.order_number}&status=cancelled"

    amount_usd = convert_kes_to_usd(order.total_price)
    unit_amount_cents = int(round(amount_usd * 100))

    secret_key = get_stripe_secret_key()
    session_id = None
    checkout_url = None

    product_desc = f"{order.product_name} (Qty: {order.quantity})"
    if order.size:
        product_desc += f", Size: {order.size}"
    if order.color:
        product_desc += f", Colour: {order.color}"

    if secret_key and not secret_key.startswith("sk_test_placeholder"):
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        form_data = {
            "mode": "payment",
            "success_url": final_success_url,
            "cancel_url": final_cancel_url,
            "client_reference_id": order.order_number,
            "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][unit_amount]": str(unit_amount_cents),
            "line_items[0][price_data][product_data][name]": f"ICP Merchandise: {order.product_name}",
            "line_items[0][price_data][product_data][description]": product_desc[:250],
            "metadata[order_number]": order.order_number,
            "metadata[purpose]": "merchandise",
            "payment_method_types[0]": "card",
        }
        if order.customer_email:
            form_data["customer_email"] = order.customer_email

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{STRIPE_API_BASE}/checkout/sessions",
                    data=form_data,
                    headers=headers,
                )
                data = resp.json()
                if resp.status_code == 200:
                    session_id = data.get("id")
                    checkout_url = data.get("url")
                else:
                    err_msg = data.get("error", {}).get("message", "Stripe API error")
                    logger.error(f"Stripe error creating merch session: {err_msg}")
                    raise RuntimeError(f"Stripe error: {err_msg}")
        except httpx.RequestError as e:
            logger.error(f"Network error contacting Stripe for merch: {e}")
            raise RuntimeError("Unable to connect to Stripe payment gateway. Please try again.")
    else:
        # Development / Simulation mode
        token = uuid.uuid4().hex[:16]
        session_id = f"cs_test_sim_{token}"
        checkout_url = final_success_url.replace("{CHECKOUT_SESSION_ID}", session_id) + "&simulated=true"
        logger.info(f"Stripe merch running in simulation mode. Generated session: {session_id}")

    # Record StripeTransaction in DB
    tx = StripeTransaction(
        id=str(uuid.uuid4()),
        user_id=None,
        order_number=order.order_number,
        session_id=session_id,
        amount=amount_usd,
        currency="USD",
        status="initiated",
        purpose="merchandise",
        customer_email=order.customer_email,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    return {
        "success": True,
        "session_id": session_id,
        "checkout_url": checkout_url,
        "amount_usd": amount_usd,
        "amount_kes": order.total_price,
        "currency": "USD",
        "order_number": order.order_number,
        "purpose": "merchandise",
    }


async def verify_and_fulfill_session(
    session_id: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Verifies checkout session status (via Stripe API or simulation)
    and fulfills the corresponding membership or merchandise order.
    Idempotent: safe to run multiple times.
    """
    clean_session_id = session_id.strip()

    # Look up existing transaction record
    stmt = select(StripeTransaction).where(
        StripeTransaction.session_id == clean_session_id
    )
    res = await db.execute(stmt)
    tx = res.scalars().first()

    now = utcnow()
    is_simulated = clean_session_id.startswith("cs_test_sim_")
    secret_key = get_stripe_secret_key()

    is_paid = False
    payment_intent_id = None
    session_data: Dict[str, Any] = {}

    if is_simulated or not secret_key or secret_key.startswith("sk_test_placeholder"):
        # Simulated or dev mode: treat as paid
        is_paid = True
        payment_intent_id = f"pi_sim_{clean_session_id[-12:]}"
    else:
        # Query Stripe API for authoritative session status
        headers = {"Authorization": f"Bearer {secret_key}"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{STRIPE_API_BASE}/checkout/sessions/{clean_session_id}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    session_data = resp.json()
                    payment_status = session_data.get("payment_status")
                    payment_intent_id = session_data.get("payment_intent")
                    if payment_status == "paid":
                        is_paid = True
                else:
                    logger.error(f"Failed to fetch Stripe session {clean_session_id}: {resp.text}")
        except Exception as e:
            logger.error(f"Error querying Stripe session: {e}")

    if not is_paid:
        return {
            "success": False,
            "status": "unpaid",
            "message": "Payment has not yet been confirmed by Stripe.",
            "session_id": clean_session_id,
        }

    # If transaction already completed, return existing fulfillment
    if tx and tx.status == "completed":
        return {
            "success": True,
            "status": "completed",
            "already_fulfilled": True,
            "purpose": tx.purpose,
            "order_number": tx.order_number,
            "message": "Payment verified and previously fulfilled.",
        }

    # Determine purpose and fulfill
    purpose = tx.purpose if tx else "membership"
    order_number = tx.order_number if tx else None

    # Check metadata from Stripe session if tx record didn't have it
    if session_data:
        meta = session_data.get("metadata", {})
        if meta.get("purpose"):
            purpose = meta.get("purpose")
        if meta.get("order_number"):
            order_number = meta.get("order_number")

    if purpose == "membership":
        user_id = tx.user_id if tx else None
        if not user_id and session_data:
            user_id = session_data.get("client_reference_id") or session_data.get("metadata", {}).get("user_id")

        if user_id:
            user_res = await db.execute(select(User).where(User.id == user_id))
            user = user_res.scalars().first()

            if user:
                # 1. Update or create Membership
                mem_res = await db.execute(
                    select(Membership).where(Membership.user_id == user.id)
                )
                mem = mem_res.scalars().first()

                fee_usd = tx.amount if tx else DEFAULT_MEMBERSHIP_PRICE_USD
                if not mem:
                    mem = Membership(
                        id=str(uuid.uuid4()),
                        user_id=user.id,
                        status="active",
                        fee_paid=fee_usd,
                        currency="USD",
                        activated_at=now,
                        notes=f"Stripe card payment verified. Session: {clean_session_id}",
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(mem)
                else:
                    mem.status = "active"
                    mem.fee_paid = fee_usd
                    mem.currency = "USD"
                    mem.activated_at = now
                    mem.notes = f"Stripe card payment verified. Session: {clean_session_id}"
                    mem.updated_at = now

                # 2. Add PaymentSubmission record
                sub_res = await db.execute(
                    select(PaymentSubmission).where(
                        PaymentSubmission.transaction_reference == clean_session_id
                    )
                )
                if not sub_res.scalars().first():
                    submission = PaymentSubmission(
                        id=str(uuid.uuid4()),
                        user_id=user.id,
                        membership_id=mem.id,
                        transaction_reference=clean_session_id,
                        payment_method="card",
                        amount=fee_usd,
                        currency="USD",
                        payer_name=user.full_name,
                        status="approved",
                        submitted_at=now,
                        verified_at=now,
                        admin_notes=f"Auto-verified via Stripe. Intent: {payment_intent_id or 'none'}",
                    )
                    db.add(submission)

                # 3. Audit log
                audit = AuditLog(
                    id=str(uuid.uuid4()),
                    admin_id=user.id,
                    action="stripe_membership_activated",
                    target_resource="memberships",
                    target_id=mem.id,
                    details=f"User {user.email} membership auto-activated via Stripe session {clean_session_id}",
                    created_at=now,
                )
                db.add(audit)

    elif purpose == "merchandise" and order_number:
        ord_res = await db.execute(
            select(MerchandiseOrder).where(MerchandiseOrder.order_number == order_number)
        )
        order = ord_res.scalars().first()
        if order:
            order.payment_status = "paid"
            order.payment_method = "stripe"
            order.payment_reference = clean_session_id
            order.status = "confirmed"
            order.updated_at = now

            audit = AuditLog(
                id=str(uuid.uuid4()),
                admin_id=order.id,
                action="merchandise_order_paid_stripe",
                target_resource="merchandise_orders",
                target_id=order.id,
                details=f"Order {order.order_number} marked as paid via Stripe session {clean_session_id}",
                created_at=now,
            )
            db.add(audit)

    # Update or create transaction record
    if not tx:
        tx = StripeTransaction(
            id=str(uuid.uuid4()),
            session_id=clean_session_id,
            payment_intent_id=payment_intent_id,
            amount=DEFAULT_MEMBERSHIP_PRICE_USD if purpose == "membership" else 0.0,
            currency="USD",
            status="completed",
            purpose=purpose,
            order_number=order_number,
            created_at=now,
            updated_at=now,
        )
        db.add(tx)
    else:
        tx.status = "completed"
        tx.payment_intent_id = payment_intent_id or tx.payment_intent_id
        tx.updated_at = now

    await db.commit()
    if tx:
        await db.refresh(tx)

    return {
        "success": True,
        "status": "completed",
        "purpose": purpose,
        "order_number": order_number,
        "session_id": clean_session_id,
        "message": "Payment verified and fulfilled successfully.",
    }


def verify_stripe_webhook_signature(
    payload_bytes: bytes,
    sig_header: str,
    secret: str,
    tolerance_seconds: int = 300,
) -> bool:
    """
    Cryptographically verifies Stripe's webhook signature header:
    t=timestamp,v1=signature
    """
    if not sig_header or not secret:
        return False

    try:
        parts = dict(item.strip().split("=", 1) for item in sig_header.split(","))
        timestamp_str = parts.get("t")
        expected_sig = parts.get("v1")

        if not timestamp_str or not expected_sig:
            return False

        # Check timestamp within tolerance
        ts = int(timestamp_str)
        current_ts = int(time.time())
        if abs(current_ts - ts) > tolerance_seconds:
            logger.warning("Stripe webhook timestamp exceeds tolerance.")
            return False

        signed_payload = f"{timestamp_str}.".encode("utf-8") + payload_bytes
        computed_sig = hmac.new(
            secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed_sig, expected_sig)
    except Exception as e:
        logger.error(f"Error checking Stripe webhook signature: {e}")
        return False

