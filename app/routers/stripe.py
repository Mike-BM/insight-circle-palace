import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import get_current_user
from app.database import get_db
from app.ratelimit import limiter
from app.security import is_production
from app.models import MerchandiseOrder, User
from app.services.stripe_service import (
    create_membership_checkout_session,
    create_merchandise_checkout_session,
    get_stripe_config,
    get_stripe_webhook_secret,
    verify_and_fulfill_session,
    verify_stripe_webhook_signature,
)

logger = logging.getLogger("stripe_router")

router = APIRouter(prefix="/api/payments/stripe", tags=["stripe"])


class MerchandiseCheckoutPayload(BaseModel):
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class MembershipCheckoutPayload(BaseModel):
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@router.get("/config")
async def get_public_stripe_configuration():
    """
    Returns public Stripe configuration parameters:
    Publishable key, membership price in USD, and currency info.
    """
    return get_stripe_config()


@router.post("/checkout/membership")
@limiter.limit("10/minute;40/hour")
async def initiate_membership_checkout(
    request: Request,
    payload: Optional[MembershipCheckoutPayload] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiates a Stripe Checkout session for the authenticated user to purchase
    Insight Circle Palace Lifetime Membership ($2.50 USD).
    """
    try:
        s_url = payload.success_url if payload else None
        c_url = payload.cancel_url if payload else None
        result = await create_membership_checkout_session(
            user=current_user,
            db=db,
            success_url=s_url,
            cancel_url=c_url,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error initiating Stripe membership checkout: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Stripe card checkout. Please try again.",
        )


@router.post("/checkout/merchandise/{order_number}")
@limiter.limit("10/minute;40/hour")
async def initiate_merchandise_checkout(
    request: Request,
    order_number: str,
    payload: Optional[MerchandiseCheckoutPayload] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Initiates a Stripe Checkout session for a specific merchandise order.
    Converts order total from KES to USD for international card payments.
    """
    clean_ord = order_number.strip().upper()
    stmt = select(MerchandiseOrder).where(MerchandiseOrder.order_number == clean_ord)
    res = await db.execute(stmt)
    order = res.scalars().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_number}' not found.",
        )

    try:
        s_url = payload.success_url if payload else None
        c_url = payload.cancel_url if payload else None
        result = await create_merchandise_checkout_session(
            order=order,
            db=db,
            success_url=s_url,
            cancel_url=c_url,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error initiating Stripe merchandise checkout: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Stripe card checkout for order.",
        )


@router.get("/verify-session/{session_id}")
@limiter.limit("30/minute")
async def verify_stripe_session(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Verifies the payment status of a Stripe Checkout Session
    and fulfills the order or activates the user's membership.
    """
    clean_id = session_id.strip()
    try:
        result = await verify_and_fulfill_session(clean_id, db)
        return result
    except Exception as e:
        logger.error(f"Error verifying Stripe session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying payment session.",
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Official Stripe Webhook endpoint.
    Handles 'checkout.session.completed' events to fulfill memberships & merchandise orders.
    """
    payload_bytes = await request.body()
    webhook_secret = get_stripe_webhook_secret()

    # The signature is ALWAYS verified in production. Without a configured secret the
    # webhook is refused, rather than silently accepting unsigned events.
    if webhook_secret:
        if not stripe_signature or not verify_stripe_webhook_signature(
            payload_bytes, stripe_signature, webhook_secret
        ):
            logger.warning("Invalid Stripe webhook signature.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            )
    elif is_production():
        logger.error("STRIPE_WEBHOOK_SECRET is not configured; refusing webhook in production.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook not configured",
        )

    try:
        event = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("type")
    logger.info(f"Received Stripe webhook event: {event_type}")

    if event_type == "checkout.session.completed":
        session_obj = event.get("data", {}).get("object", {})
        session_id = session_obj.get("id")
        if session_id:
            await verify_and_fulfill_session(session_id, db)

    return {"status": "success", "received": True}

