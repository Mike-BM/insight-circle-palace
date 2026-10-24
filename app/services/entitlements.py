import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    Program,
    ProgramEntitlement,
    PaymentAccessRequest,
    Enrollment,
    Module,
    Lesson,
    utcnow,
)


async def check_user_access(
    user: Optional[User],
    program_id: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Evaluates whether a user is authorized to access a given program's full paid content.
    Returns a dictionary detailing access status, reason, pricing, and pending requests.
    """
    # 1. Unauthenticated users cannot have paid access
    if not user:
        return {
            "has_access": False,
            "status": "unauthenticated",
            "message": "Authentication required to access learning content.",
        }

    # 2. Administrative roles always have unrestricted preview and review access
    admin_roles = ["admin", "super_admin", "editor", "program_manager"]
    if user.role in admin_roles:
        return {
            "has_access": True,
            "status": "admin",
            "message": "Administrator privileges granted.",
        }

    # 3. Fetch Program metadata
    prog_res = await db.execute(select(Program).where(Program.id == program_id))
    program = prog_res.scalars().first()
    if not program:
        return {
            "has_access": False,
            "status": "not_found",
            "message": "Program not found.",
        }

    # 4. Check if program is explicitly configured as free / open-access
    if getattr(program, "is_paid", True) is False or (
        getattr(program, "price_kes", 0.0) == 0.0
        and getattr(program, "price_usd", 0.0) == 0.0
    ):
        return {
            "has_access": True,
            "status": "free",
            "message": "Complimentary open-access program.",
        }

    # 5. Check active user entitlements (program-specific or all-access subscription)
    ent_res = await db.execute(
        select(ProgramEntitlement).where(
            ProgramEntitlement.user_id == user.id,
            ProgramEntitlement.status == "active",
        )
    )
    entitlements = ent_res.scalars().all()
    now = utcnow()

    for ent in entitlements:
        # Check expiration
        if ent.expires_at and ent.expires_at <= now:
            ent.status = "expired"
            ent.updated_at = now
            await db.commit()
            continue

        # All-access subscription grants access to all programs
        if ent.entitlement_type == "subscription":
            return {
                "has_access": True,
                "status": "subscription",
                "expires_at": ent.expires_at.isoformat() if ent.expires_at else None,
                "message": "Active all-access membership subscription.",
            }

        # Program-specific purchase
        if ent.program_id == program_id:
            return {
                "has_access": True,
                "status": "program_purchase",
                "expires_at": ent.expires_at.isoformat() if ent.expires_at else None,
                "message": "Program access verified.",
            }

    # 6. Check if learner has a pending manual payment access request under review
    req_res = await db.execute(
        select(PaymentAccessRequest).where(
            PaymentAccessRequest.user_id == user.id,
            PaymentAccessRequest.status == "pending",
            or_(
                PaymentAccessRequest.program_id == program_id,
                PaymentAccessRequest.request_type == "subscription",
            ),
        ).order_by(PaymentAccessRequest.created_at.desc())
    )
    pending_req = req_res.scalars().first()
    if pending_req:
        return {
            "has_access": False,
            "status": "pending_approval",
            "message": "Your payment access request is under review by administration.",
            "pending_request": {
                "id": pending_req.id,
                "transaction_reference": pending_req.transaction_reference,
                "payment_method": pending_req.payment_method,
                "amount": pending_req.amount,
                "currency": pending_req.currency,
                "submitted_at": pending_req.created_at.isoformat() if pending_req.created_at else None,
            },
        }

    # 7. Access requires payment
    return {
        "has_access": False,
        "status": "payment_required",
        "message": "Paid enrollment required to unlock complete lessons and recordings.",
        "price_kes": getattr(program, "price_kes", 0.0),
        "price_usd": getattr(program, "price_usd", 0.0),
        "payment_instructions": getattr(program, "payment_instructions", None),
    }


async def grant_program_entitlement(
    user_id: str,
    entitlement_type: str,
    program_id: Optional[str],
    granter_id: Optional[str],
    payment_request_id: Optional[str] = None,
    expiry_days: Optional[int] = None,
    db: AsyncSession = None,
) -> ProgramEntitlement:
    """
    Grants an active entitlement, calculates expiry if applicable, and automatically initializes enrollment.
    """
    now = utcnow()
    expires_at = None
    if expiry_days and expiry_days > 0:
        expires_at = now + timedelta(days=expiry_days)

    entitlement = ProgramEntitlement(
        id=str(uuid.uuid4()),
        user_id=user_id,
        entitlement_type=entitlement_type,
        program_id=program_id,
        payment_request_id=payment_request_id,
        status="active",
        start_date=now,
        expires_at=expires_at,
        granted_by=granter_id,
        created_at=now,
        updated_at=now,
    )
    db.add(entitlement)

    # If granting program-specific access, ensure Enrollment is initialized
    if program_id:
        enr_res = await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.program_id == program_id,
            )
        )
        existing_enr = enr_res.scalars().first()
        if not existing_enr:
            first_lesson_id = None
            first_mod_res = await db.execute(
                select(Module).where(Module.program_id == program_id).order_by(Module.order)
            )
            first_mod = first_mod_res.scalars().first()
            if first_mod:
                first_less_res = await db.execute(
                    select(Lesson).where(Lesson.module_id == first_mod.id).order_by(Lesson.order)
                )
                first_less = first_less_res.scalars().first()
                if first_less:
                    first_lesson_id = first_less.id

            new_enr = Enrollment(
                id=str(uuid.uuid4()),
                user_id=user_id,
                program_id=program_id,
                status="in_progress",
                last_accessed_lesson_id=first_lesson_id,
                enrolled_at=now,
            )
            db.add(new_enr)

    await db.commit()
    await db.refresh(entitlement)
    return entitlement
