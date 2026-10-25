import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    User,
    Program,
    PaymentAccessRequest,
    ProgramEntitlement,
    AuditLog,
    utcnow,
)
from app.schemas import (
    PaymentRequestCreate,
    PaymentRequestOut,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])

DEFAULT_PAYMENT_CONFIG = {
    "mpesa_till_number": "3491023",
    "mpesa_till_name": "Insight Circle Palace",
    "mpesa_paybill_business_no": "522522",
    "mpesa_paybill_account_no": "1314902847",
    "bank_name": "KCB Bank Kenya",
    "bank_account_name": "Insight Circle Palace Limited",
    "bank_account_number": "1314902847",
    "bank_branch": "Nairobi Central",
    "currency_options": ["KES", "USD"],
    "support_contact": "payments@insightcirclepalace.org",
}


@router.get("/info")
async def get_payment_info():
    """
    Returns public verified manual payment instructions and accounts.
    """
    return {
        "status": "success",
        "payment_instructions": DEFAULT_PAYMENT_CONFIG,
        "subscription_plans": [
            {
                "id": "all_access_monthly",
                "name": "All-Access Monthly Pass",
                "price_kes": 3500.0,
                "price_usd": 29.0,
                "duration_days": 30,
                "description": "Unrestricted access to all 9 leadership, technology, finance, and venture pathways for 30 days.",
            },
            {
                "id": "all_access_annual",
                "name": "Executive Annual Membership",
                "price_kes": 32000.0,
                "price_usd": 260.0,
                "duration_days": 365,
                "description": "Full access to all pathways, masterclasses, assignments, and verified certificates for 1 full year.",
            },
        ],
    }


@router.post("/request-access", response_model=PaymentRequestOut)
async def submit_payment_access_request(
    payload: PaymentRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Learner submits proof of manual payment for a specific program or subscription.
    """
    clean_ref = payload.transaction_reference.strip().upper()
    if len(clean_ref) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction reference code must be at least 4 characters.",
        )

    program = None
    if payload.item_type == "program":
        if not payload.program_slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Program slug is required for program purchase requests.",
            )
        prog_res = await db.execute(select(Program).where(Program.slug == payload.program_slug))
        program = prog_res.scalars().first()
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Program '{payload.program_slug}' not found.",
            )

        # Check if user is already entitled to this program
        ent_res = await db.execute(
            select(ProgramEntitlement).where(
                ProgramEntitlement.user_id == current_user.id,
                ProgramEntitlement.program_id == program.id,
                ProgramEntitlement.status == "active",
            )
        )
        if ent_res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active verified entitlement for this program.",
            )

        # Check for existing pending request for this program
        dup_user_res = await db.execute(
            select(PaymentAccessRequest).where(
                PaymentAccessRequest.user_id == current_user.id,
                PaymentAccessRequest.program_id == program.id,
                PaymentAccessRequest.status == "pending",
            )
        )
        if dup_user_res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have a pending access request for this program under review.",
            )

    # Check for duplicate transaction reference across any pending request
    ref_res = await db.execute(
        select(PaymentAccessRequest).where(
            PaymentAccessRequest.transaction_reference == clean_ref,
            PaymentAccessRequest.status == "pending",
        )
    )
    if ref_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A payment request with this transaction reference code is already being processed.",
        )

    # Calculate expected amount if not provided
    amount = payload.amount
    if (not amount or amount <= 0) and program:
        amount = getattr(program, "price_kes", 0.0) or getattr(program, "price_usd", 0.0) or 0.0

    now = utcnow()
    req = PaymentAccessRequest(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        request_type=payload.item_type,
        program_id=program.id if program else None,
        subscription_plan=payload.subscription_plan if payload.item_type == "subscription" else None,
        amount=amount,
        currency=payload.currency.upper(),
        payment_method=payload.payment_method,
        transaction_reference=clean_ref,
        notes=payload.notes.strip() if payload.notes else None,
        proof_image_url=payload.proof_image_url,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(req)

    # Audit log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        admin_id=current_user.id,
        action="payment_request_submitted",
        target_resource="payment_access_requests",
        target_id=req.id,
        details=f"Learner {current_user.email} submitted payment ref {clean_ref} for {payload.item_type}",
        created_at=now,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(req)

    return PaymentRequestOut(
        id=req.id,
        user_id=req.user_id,
        user_name=current_user.full_name,
        user_email=current_user.email,
        request_type=req.request_type,
        program_id=req.program_id,
        program_slug=program.slug if program else None,
        program_title=program.title if program else None,
        subscription_plan=req.subscription_plan,
        amount=req.amount,
        currency=req.currency,
        payment_method=req.payment_method,
        transaction_reference=req.transaction_reference,
        notes=req.notes,
        proof_image_url=req.proof_image_url,
        status=req.status,
        created_at=req.created_at,
    )


@router.get("/my-requests", response_model=List[PaymentRequestOut])
async def list_my_payment_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all payment access requests submitted by the current authenticated learner.
    """
    stmt = (
        select(PaymentAccessRequest)
        .options(selectinload(PaymentAccessRequest.program))
        .where(PaymentAccessRequest.user_id == current_user.id)
        .order_by(PaymentAccessRequest.created_at.desc())
    )
    result = await db.execute(stmt)
    requests = result.scalars().all()

    output = []
    for r in requests:
        output.append(
            PaymentRequestOut(
                id=r.id,
                user_id=r.user_id,
                user_name=current_user.full_name,
                user_email=current_user.email,
                request_type=r.request_type,
                program_id=r.program_id,
                program_slug=r.program.slug if r.program else None,
                program_title=r.program.title if r.program else None,
                subscription_plan=r.subscription_plan,
                amount=r.amount,
                currency=r.currency,
                payment_method=r.payment_method,
                transaction_reference=r.transaction_reference,
                notes=r.notes,
                proof_image_url=r.proof_image_url,
                status=r.status,
                admin_notes=r.admin_notes,
                approved_by=r.approved_by,
                approved_at=r.approved_at,
                created_at=r.created_at,
            )
        )
    return output
