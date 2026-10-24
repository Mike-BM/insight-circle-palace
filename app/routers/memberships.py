from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_admin, get_current_user
from app.database import get_db
from app.models import AuditLog, Membership, PaymentSubmission, User, utcnow
from app.schemas import (MembershipConfigOut, MembershipConfigUpdate,
                         MembershipGrantAction, MembershipStatusOut,
                         PaymentSubmissionCreate, PaymentSubmissionOut,
                         PaymentVerificationAction)
from app.services.membership import (calculate_expiry, check_user_membership,
                                     get_membership_config,
                                     save_membership_config)

router = APIRouter(prefix="/api/membership", tags=["membership"])
admin_membership_router = APIRouter(
    prefix="/api/admin/memberships", tags=["admin-memberships"]
)


# --- Public / Member Endpoints ---


@router.get("/config", response_model=MembershipConfigOut)
async def get_public_membership_config(db: AsyncSession = Depends(get_db)):
    """
    Public endpoint providing current membership fee, currency, access duration,
    and payment instructions.
    """
    cfg = await get_membership_config(db)
    return MembershipConfigOut(
        fee=cfg.get("fee", 1500.0),
        currency=cfg.get("currency", "KES"),
        duration_value=cfg.get("duration_value", 30),
        duration_unit=cfg.get("duration_unit", "days"),
        is_configured=cfg.get("is_configured", True),
        payment_instructions=cfg.get("payment_instructions"),
        paybill_number=cfg.get("paybill_number"),
        account_reference=cfg.get("account_reference"),
    )


@router.get("/my-status", response_model=MembershipStatusOut)
async def get_my_membership_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the authenticated user's current verified membership status,
    active expiration timestamp, remaining days, and pending payment submission if any.
    """
    mem_status = await check_user_membership(current_user, db)
    cfg = await get_membership_config(db)

    # Check for recent pending submission
    pending_stmt = (
        select(PaymentSubmission)
        .where(PaymentSubmission.user_id == current_user.id)
        .where(PaymentSubmission.status == "pending")
        .order_by(desc(PaymentSubmission.submitted_at))
    )
    pending_res = await db.execute(pending_stmt)
    pending_sub = pending_res.scalars().first()

    pending_dict = None
    if pending_sub:
        pending_dict = {
            "id": pending_sub.id,
            "transaction_reference": pending_sub.transaction_reference,
            "amount": pending_sub.amount,
            "currency": pending_sub.currency,
            "submitted_at": (
                pending_sub.submitted_at.isoformat()
                if pending_sub.submitted_at
                else None
            ),
        }

    return MembershipStatusOut(
        user_id=current_user.id,
        has_access=mem_status["has_access"],
        status=mem_status["status"],
        is_admin=mem_status.get("is_admin", False),
        activated_at=mem_status.get("activated_at"),
        expires_at=mem_status.get("expires_at"),
        days_remaining=mem_status.get("days_remaining"),
        membership_id=mem_status.get("membership_id"),
        pending_submission=pending_dict,
        config=cfg,
    )


@router.post("/submit-payment", status_code=201)
async def submit_membership_payment(
    payment_in: PaymentSubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits a payment reference for manual verification by administrators.
    Enforces transaction reference uniqueness to prevent duplicate claims.
    """
    clean_ref = payment_in.transaction_reference.strip().upper()
    if len(clean_ref) < 4:
        raise HTTPException(
            status_code=400, detail="Transaction reference is too short."
        )

    # Check uniqueness of transaction reference
    ref_check = await db.execute(
        select(PaymentSubmission).where(
            PaymentSubmission.transaction_reference == clean_ref
        )
    )
    if ref_check.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="This transaction reference has already been submitted.",
        )

    # Find or create a pending membership for this user
    mem_check = await db.execute(
        select(Membership)
        .where(Membership.user_id == current_user.id)
        .order_by(desc(Membership.created_at))
    )
    existing_mem = mem_check.scalars().first()

    if not existing_mem or existing_mem.status in [
        "expired",
        "revoked",
        "rejected",
    ]:
        mem = Membership(
            user_id=current_user.id,
            status="pending",
            fee_paid=payment_in.amount,
            currency=payment_in.currency.upper(),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(mem)
        await db.flush()
        membership_id = mem.id
    else:
        membership_id = existing_mem.id

    payment = PaymentSubmission(
        user_id=current_user.id,
        membership_id=membership_id,
        transaction_reference=clean_ref,
        payment_method=payment_in.payment_method.lower(),
        amount=payment_in.amount,
        currency=payment_in.currency.upper(),
        payer_name=payment_in.payer_name,
        payer_phone=payment_in.payer_phone,
        status="pending",
        submitted_at=utcnow(),
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return {
        "status": "pending_verification",
        "payment_id": payment.id,
        "message": "Payment submitted successfully. Your membership access will activate upon verification by our administrators.",
        "transaction_reference": clean_ref,
    }


# --- Administrator Membership & Verification Endpoints ---


@admin_membership_router.get("/config")
async def admin_get_membership_config(
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_membership_config(db)


@admin_membership_router.post("/config")
async def admin_update_membership_config(
    config_in: MembershipConfigUpdate,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    new_cfg = config_in.model_dump()
    saved = await save_membership_config(db, new_cfg)

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Update Membership Config",
        target_resource="SystemSettings",
        details=f"Fee: {saved.get('fee')} {saved.get('currency')}, Duration: {saved.get('duration_value')} {saved.get('duration_unit')}",
        created_at=utcnow(),
    )
    db.add(audit)
    await db.commit()
    return saved


@admin_membership_router.get(
    "/payments", response_model=List[PaymentSubmissionOut]
)
async def admin_list_payments(
    status: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PaymentSubmission)
        .options(selectinload(PaymentSubmission.user))
        .order_by(desc(PaymentSubmission.submitted_at))
    )

    if status and status.lower() != "all":
        stmt = stmt.where(PaymentSubmission.status == status.lower())

    result = await db.execute(stmt)
    payments = result.scalars().all()

    out = []
    for p in payments:
        out.append(
            PaymentSubmissionOut(
                id=p.id,
                user_id=p.user_id,
                user_name=p.user.full_name if p.user else "Unknown User",
                user_email=p.user.email if p.user else "Unknown Email",
                transaction_reference=p.transaction_reference,
                payment_method=p.payment_method,
                amount=p.amount,
                currency=p.currency,
                payer_name=p.payer_name,
                payer_phone=p.payer_phone,
                status=p.status,
                submitted_at=p.submitted_at,
                verified_at=p.verified_at,
                verified_by=p.verified_by,
                admin_notes=p.admin_notes,
            )
        )
    return out


@admin_membership_router.post("/payments/{payment_id}/verify")
async def admin_verify_payment(
    payment_id: str,
    action_in: PaymentVerificationAction,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PaymentSubmission)
        .options(selectinload(PaymentSubmission.membership))
        .where(PaymentSubmission.id == payment_id)
    )
    payment = result.scalars().first()
    if not payment:
        raise HTTPException(
            status_code=404, detail="Payment submission not found"
        )

    now = utcnow()
    cfg = await get_membership_config(db)
    dur_val = cfg.get("duration_value", 30)
    dur_unit = cfg.get("duration_unit", "days")

    if action_in.action in ("approve", "approved"):
        payment.status = "approved"
        payment.verified_at = now
        payment.verified_by = admin_user.id
        payment.admin_notes = action_in.admin_notes

        # Compute membership expiry
        # If user currently has active membership with remaining time, extend it!
        base_time = now
        mem = payment.membership
        if (
            mem
            and mem.status == "active"
            and mem.expires_at
            and (mem.expires_at.replace(tzinfo=timezone.utc) if mem.expires_at.tzinfo is None else mem.expires_at) > now
        ):
            base_time = mem.expires_at.replace(tzinfo=timezone.utc) if mem.expires_at.tzinfo is None else mem.expires_at

        expiry_dt = calculate_expiry(dur_val, dur_unit, base_time)

        if not mem:
            mem = Membership(
                user_id=payment.user_id,
                status="active",
                fee_paid=payment.amount,
                currency=payment.currency,
                activated_at=now,
                expires_at=expiry_dt,
                granted_by=admin_user.id,
                created_at=now,
                updated_at=now,
            )
            db.add(mem)
            await db.flush()
            payment.membership_id = mem.id
        else:
            mem.status = "active"
            if not mem.activated_at:
                mem.activated_at = now
            mem.expires_at = expiry_dt
            mem.granted_by = admin_user.id
            mem.fee_paid = payment.amount
            mem.currency = payment.currency
            mem.updated_at = now

        audit = AuditLog(
            admin_id=admin_user.id,
            action="Membership Payment Approved",
            target_resource="PaymentSubmission",
            target_id=payment.id,
            details=f"Approved payment {payment.transaction_reference} for user {payment.user_id}. Access granted until {expiry_dt.isoformat()}. Notes: {action_in.admin_notes or 'None'}",
            created_at=now,
        )
        db.add(audit)
        await db.commit()

        return {
            "status": "approved",
            "message": "Payment verified and membership activated.",
            "expires_at": expiry_dt.isoformat(),
        }

    else:  # reject
        payment.status = "rejected"
        payment.verified_at = now
        payment.verified_by = admin_user.id
        payment.admin_notes = action_in.admin_notes

        if payment.membership and payment.membership.status == "pending":
            payment.membership.status = "rejected"
            payment.membership.updated_at = now

        audit = AuditLog(
            admin_id=admin_user.id,
            action="Reject Membership Payment",
            target_resource="PaymentSubmission",
            target_id=payment.id,
            details=f"Rejected payment {payment.transaction_reference}. Reason: {action_in.admin_notes or 'Not specified'}",
            created_at=now,
        )
        db.add(audit)
        await db.commit()

        return {"status": "rejected", "message": "Payment marked as rejected."}


@admin_membership_router.post("/grant")
async def admin_grant_membership(
    grant_in: MembershipGrantAction,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Directly grant or extend membership access for a user.
    """
    user_res = await db.execute(
        select(User).where(User.id == grant_in.user_id)
    )
    target_user = user_res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    cfg = await get_membership_config(db)
    dur_val = grant_in.duration_days or cfg.get("duration_value", 30)
    dur_unit = "days" if grant_in.duration_days else cfg.get("duration_unit", "days")

    now = utcnow()
    mem_res = await db.execute(
        select(Membership)
        .where(Membership.user_id == target_user.id)
        .order_by(desc(Membership.created_at))
    )
    mem = mem_res.scalars().first()

    base_time = now
    if mem and mem.status == "active" and mem.expires_at and mem.expires_at > now:
        base_time = mem.expires_at

    expiry_dt = calculate_expiry(dur_val, dur_unit, base_time)

    if not mem or mem.status in ["revoked", "expired", "rejected"]:
        mem = Membership(
            user_id=target_user.id,
            status="active",
            fee_paid=0.0,
            currency=cfg.get("currency", "KES"),
            activated_at=now,
            expires_at=expiry_dt,
            granted_by=admin_user.id,
            notes=grant_in.notes or "Admin direct grant",
            created_at=now,
            updated_at=now,
        )
        db.add(mem)
    else:
        mem.status = "active"
        if not mem.activated_at:
            mem.activated_at = now
        mem.expires_at = expiry_dt
        mem.granted_by = admin_user.id
        if grant_in.notes:
            mem.notes = grant_in.notes
        mem.updated_at = now

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Direct Membership Grant",
        target_resource="Membership",
        target_id=mem.id,
        details=f"Granted membership to {target_user.email} until {expiry_dt.isoformat()}.",
        created_at=now,
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "message": f"Membership granted for {target_user.full_name}.",
        "expires_at": expiry_dt.isoformat(),
    }


@admin_membership_router.post("/{membership_id}/revoke")
async def admin_revoke_membership(
    membership_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke membership immediately.
    """
    result = await db.execute(
        select(Membership).where(Membership.id == membership_id)
    )
    mem = result.scalars().first()
    if not mem:
        raise HTTPException(status_code=404, detail="Membership not found")

    now = utcnow()
    mem.status = "revoked"
    mem.expires_at = now
    mem.updated_at = now

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Revoke Membership",
        target_resource="Membership",
        target_id=mem.id,
        details=f"Revoked membership for user {mem.user_id}.",
        created_at=now,
    )
    db.add(audit)
    await db.commit()

    return {"status": "success", "message": "Membership revoked successfully."}
