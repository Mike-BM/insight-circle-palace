from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_admin, get_current_user
from app.database import get_db
from app.models import (AuditLog, Membership, MondayRegistration,
                        PaymentSubmission, User, utcnow)
from app.schemas import (ManualPaymentVerifyRequest, MemberOverviewOut,
                          MembershipActionRequest, MembershipConfigOut,
                          MembershipConfigUpdate, MembershipGrantAction,
                          MembershipStatusOut, PaymentSubmissionCreate,
                          PaymentSubmissionOut, PaymentVerificationAction)
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
@router.get("/status", response_model=MembershipStatusOut)
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


@admin_membership_router.get("/overview", response_model=List[MemberOverviewOut])
async def admin_get_members_overview(
    status: Optional[str] = Query("all"),
    search: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a comprehensive, searchable list of all registered users alongside their
    membership status, payment verification records, access activation/expiry dates,
    and Monday sessions attendance.
    """
    # 1. Query users (exclude system internal accounts if any)
    users_stmt = select(User).order_by(desc(User.created_at))
    users_res = await db.execute(users_stmt)
    all_users = users_res.scalars().all()

    # 2. Query all memberships
    mem_stmt = select(Membership).order_by(desc(Membership.created_at))
    mem_res = await db.execute(mem_stmt)
    all_mems = mem_res.scalars().all()

    user_mems: Dict[str, List[Membership]] = {}
    for m in all_mems:
        user_mems.setdefault(m.user_id, []).append(m)

    # 3. Query all payments
    pay_stmt = select(PaymentSubmission).order_by(desc(PaymentSubmission.submitted_at))
    pay_res = await db.execute(pay_stmt)
    all_payments = pay_res.scalars().all()

    user_payments: Dict[str, List[PaymentSubmission]] = {}
    for p in all_payments:
        user_payments.setdefault(p.user_id, []).append(p)

    # 4. Query Monday registrations counts
    monday_stmt = select(MondayRegistration.email)
    monday_res = await db.execute(monday_stmt)
    monday_emails = monday_res.scalars().all()
    monday_counts: Dict[str, int] = {}
    for em in monday_emails:
        clean_em = em.lower().strip()
        monday_counts[clean_em] = monday_counts.get(clean_em, 0) + 1

    # 5. Cache admin users for verifier name/email lookup
    admin_names: Dict[str, str] = {}
    admin_emails: Dict[str, str] = {}
    for u in all_users:
        admin_names[u.id] = u.full_name
        admin_emails[u.id] = u.email

    now = datetime.now(timezone.utc)
    overview_list: List[MemberOverviewOut] = []

    for u in all_users:
        m_list = user_mems.get(u.id, [])
        latest_mem = m_list[0] if m_list else None

        p_list = user_payments.get(u.id, [])
        latest_pay = p_list[0] if p_list else None

        # Determine membership status
        mem_status = "registered"
        if u.status == "suspended" or (latest_mem and latest_mem.status in ["suspended", "revoked"]):
            mem_status = "suspended" if (u.status == "suspended" or (latest_mem and latest_mem.status == "suspended")) else "revoked"
        elif latest_mem and latest_mem.status == "active":
            exp = latest_mem.expires_at
            if exp:
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp < now:
                    mem_status = "expired"
                else:
                    mem_status = "paid"
            else:
                mem_status = "paid"
        elif (latest_pay and latest_pay.status == "pending") or (latest_mem and latest_mem.status == "pending"):
            mem_status = "pending_verification"
        elif latest_mem and latest_mem.status == "expired":
            mem_status = "expired"
        else:
            mem_status = "registered"

        # Payment status
        pay_status = latest_pay.status if latest_pay else "unpaid"
        tx_ref = latest_pay.transaction_reference if latest_pay else None
        pay_method = latest_pay.payment_method if latest_pay else None
        amount = latest_pay.amount if latest_pay else (latest_mem.fee_paid if latest_mem else None)
        currency = latest_pay.currency if latest_pay else (latest_mem.currency if latest_mem else "KES")
        admin_notes = (latest_pay.admin_notes if latest_pay and latest_pay.admin_notes else (latest_mem.notes if latest_mem else None))

        verifier_id = latest_pay.verified_by if (latest_pay and latest_pay.verified_by) else (latest_mem.granted_by if latest_mem else None)
        verifier_name = admin_names.get(verifier_id) if verifier_id else None
        verifier_email = admin_emails.get(verifier_id) if verifier_id else None
        verified_at = latest_pay.verified_at if (latest_pay and latest_pay.verified_at) else (latest_mem.activated_at if latest_mem else None)

        activated_at = latest_mem.activated_at if latest_mem else None
        expires_at = latest_mem.expires_at if latest_mem else None
        monday_cnt = monday_counts.get(u.email.lower().strip(), 0)

        # Filter check
        st = status.lower() if status else "all"
        if st in ("unpaid", "registered") and mem_status != "registered":
            continue
        elif st in ("pending", "pending_verification") and mem_status != "pending_verification":
            continue
        elif st in ("paid", "approved", "active") and mem_status != "paid":
            continue
        elif st == "expired" and mem_status != "expired":
            continue
        elif st in ("suspended", "revoked") and mem_status not in ("suspended", "revoked"):
            continue

        # Search check
        if search:
            s = search.lower().strip()
            name_match = s in u.full_name.lower()
            email_match = s in u.email.lower()
            ref_match = bool(tx_ref and s in tx_ref.lower())
            if not (name_match or email_match or ref_match):
                continue

        overview_list.append(
            MemberOverviewOut(
                user_id=u.id,
                full_name=u.full_name,
                email=u.email,
                registered_at=u.created_at,
                user_status=u.status,
                user_role=u.role,
                membership_id=latest_mem.id if latest_mem else None,
                membership_status=mem_status,
                payment_id=latest_pay.id if latest_pay else None,
                payment_status=pay_status,
                transaction_reference=tx_ref,
                payment_method=pay_method,
                amount=amount,
                currency=currency,
                activated_at=activated_at,
                expires_at=expires_at,
                verified_by_name=verifier_name,
                verified_by_email=verifier_email,
                verified_at=verified_at,
                admin_notes=admin_notes,
                monday_sessions_count=monday_cnt,
            )
        )

    return overview_list


@admin_membership_router.post("/manual-verify")
async def admin_manual_verify(
    verify_in: ManualPaymentVerifyRequest,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually verifies and activates membership access for a user.
    Records the transaction reference, verification timestamp, admin auditor,
    and configurable duration.
    """
    user_res = await db.execute(select(User).where(User.id == verify_in.user_id))
    target_user = user_res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    clean_ref = verify_in.transaction_reference.strip().upper()
    now = utcnow()
    ver_date = verify_in.verification_date or now

    # Duplicate transaction reference validation
    ref_check = await db.execute(
        select(PaymentSubmission).where(PaymentSubmission.transaction_reference == clean_ref)
    )
    existing_pay_with_ref = ref_check.scalars().first()
    if existing_pay_with_ref and existing_pay_with_ref.user_id != target_user.id and existing_pay_with_ref.status == "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Transaction reference '{clean_ref}' has already been verified for another user.",
        )

    # Configured access period
    cfg = await get_membership_config(db)
    dur_val = verify_in.duration_days or cfg.get("duration_value", 30)
    dur_unit = "days" if verify_in.duration_days else cfg.get("duration_unit", "days")

    # Check target user's existing membership
    mem_res = await db.execute(
        select(Membership)
        .where(Membership.user_id == target_user.id)
        .order_by(desc(Membership.created_at))
    )
    mem = mem_res.scalars().first()

    base_time = ver_date
    if mem and mem.status == "active" and mem.expires_at:
        cur_exp = mem.expires_at.replace(tzinfo=timezone.utc) if mem.expires_at.tzinfo is None else mem.expires_at
        if cur_exp > ver_date:
            base_time = cur_exp

    expiry_dt = calculate_expiry(dur_val, dur_unit, base_time)

    # Create or update payment submission
    if verify_in.payment_id:
        pay_res = await db.execute(
            select(PaymentSubmission).where(PaymentSubmission.id == verify_in.payment_id)
        )
        pay = pay_res.scalars().first()
    elif existing_pay_with_ref and existing_pay_with_ref.user_id == target_user.id:
        pay = existing_pay_with_ref
    else:
        pay = None

    if not pay:
        pay = PaymentSubmission(
            user_id=target_user.id,
            transaction_reference=clean_ref,
            payment_method=verify_in.payment_method.lower(),
            amount=verify_in.amount,
            currency=verify_in.currency.upper(),
            payer_name=verify_in.payer_name or target_user.full_name,
            payer_phone=verify_in.payer_phone or target_user.phone,
            status="approved",
            submitted_at=ver_date,
            verified_at=ver_date,
            verified_by=admin_user.id,
            admin_notes=verify_in.admin_notes,
        )
        db.add(pay)
        await db.flush()
    else:
        pay.transaction_reference = clean_ref
        pay.amount = verify_in.amount
        pay.currency = verify_in.currency.upper()
        pay.payment_method = verify_in.payment_method.lower()
        pay.status = "approved"
        pay.verified_at = ver_date
        pay.verified_by = admin_user.id
        if verify_in.admin_notes:
            pay.admin_notes = verify_in.admin_notes

    # Create or update membership
    if not mem or mem.status in ["revoked", "suspended", "expired", "rejected"]:
        mem = Membership(
            user_id=target_user.id,
            status="active",
            fee_paid=verify_in.amount,
            currency=verify_in.currency.upper(),
            activated_at=ver_date,
            expires_at=expiry_dt,
            granted_by=admin_user.id,
            notes=verify_in.admin_notes,
            created_at=now,
            updated_at=now,
        )
        db.add(mem)
        await db.flush()
    else:
        mem.status = "active"
        if not mem.activated_at:
            mem.activated_at = ver_date
        mem.expires_at = expiry_dt
        mem.granted_by = admin_user.id
        mem.fee_paid = verify_in.amount
        mem.currency = verify_in.currency.upper()
        if verify_in.admin_notes:
            mem.notes = verify_in.admin_notes
        mem.updated_at = now

    pay.membership_id = mem.id

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Manual Payment Verified & Activated",
        target_resource="Membership",
        target_id=mem.id,
        details=(
            f"Admin {admin_user.email} verified payment '{clean_ref}' for {target_user.email}. "
            f"Amount: {verify_in.amount} {verify_in.currency}. "
            f"Access active from {ver_date.isoformat()} until {expiry_dt.isoformat()}. "
            f"Notes: {verify_in.admin_notes or 'None'}"
        ),
        created_at=now,
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "paid",
        "message": f"Payment {clean_ref} verified and membership activated for {target_user.full_name}.",
        "user_id": target_user.id,
        "membership_id": mem.id,
        "transaction_reference": clean_ref,
        "activated_at": ver_date.isoformat(),
        "expires_at": expiry_dt.isoformat(),
    }


@admin_membership_router.post("/payments/{payment_id}/keep-pending")
async def admin_keep_payment_pending(
    payment_id: str,
    action_in: Optional[PaymentVerificationAction] = None,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Keep payment submission in pending review queue with optional admin audit note.
    """
    result = await db.execute(
        select(PaymentSubmission).where(PaymentSubmission.id == payment_id)
    )
    pay = result.scalars().first()
    if not pay:
        raise HTTPException(status_code=404, detail="Payment submission not found")

    now = utcnow()
    notes = action_in.admin_notes if (action_in and action_in.admin_notes) else "Under review by admin"
    pay.status = "pending"
    pay.admin_notes = notes

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Keep Payment Pending",
        target_resource="PaymentSubmission",
        target_id=pay.id,
        details=f"Payment {pay.transaction_reference} kept pending by {admin_user.email}. Notes: {notes}",
        created_at=now,
    )
    db.add(audit)
    await db.commit()

    return {"status": "pending", "message": "Payment kept in review queue."}


@admin_membership_router.post("/user/{user_id}/suspend")
async def admin_suspend_user_membership(
    user_id: str,
    req_in: Optional[MembershipActionRequest] = None,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Suspend or revoke membership access for a user.
    """
    mem_res = await db.execute(
        select(Membership).where(Membership.user_id == user_id).order_by(desc(Membership.created_at))
    )
    mem = mem_res.scalars().first()
    now = utcnow()
    notes = req_in.admin_notes if req_in else None

    if mem:
        mem.status = "suspended"
        mem.expires_at = now
        mem.updated_at = now
        if notes:
            mem.notes = f"{mem.notes or ''}\n[Suspended]: {notes}".strip()

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Suspend Membership",
        target_resource="Membership",
        target_id=mem.id if mem else user_id,
        details=f"Admin {admin_user.email} suspended membership for user {user_id}. Reason: {notes or 'Not specified'}",
        created_at=now,
    )
    db.add(audit)
    await db.commit()

    return {"status": "suspended", "message": "Membership successfully suspended."}

