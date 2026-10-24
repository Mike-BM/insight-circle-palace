import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Membership, SystemSettings, User, utcnow

DEFAULT_MEMBERSHIP_CONFIG: Dict[str, Any] = {
    "fee": 1500.0,
    "currency": "KES",
    "duration_value": 30,
    "duration_unit": "days",  # "days", "months", "years"
    "is_configured": True,
    "payment_instructions": (
        "Pay via M-Pesa:\n"
        "1. Go to M-Pesa on your phone.\n"
        "2. Select Send Money / Till Number: +254 768 371 417 (Insight Circle Palace).\n"
        "3. Enter the exact membership fee amount.\n"
        "4. Confirm payment with your M-Pesa PIN.\n"
        "5. Enter the M-Pesa transaction reference code (e.g. RKA7XYZ123) below to verify."
    ),
    "paybill_number": "+254 768 371 417",
    "account_reference": "ICP Membership",
}

ADMIN_ROLES = [
    "admin",
    "super_admin",
    "editor",
    "event_manager",
    "program_manager",
    "certificate_manager",
    "moderator",
]


async def get_membership_config(db: AsyncSession) -> Dict[str, Any]:
    """
    Fetches centralized membership pricing, duration, and instructions from system settings.
    """
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "membership_config")
    )
    setting = result.scalars().first()
    if setting and setting.value:
        try:
            stored = json.loads(setting.value)
            cfg = DEFAULT_MEMBERSHIP_CONFIG.copy()
            cfg.update(stored)
            return cfg
        except Exception:
            pass
    return DEFAULT_MEMBERSHIP_CONFIG.copy()


async def save_membership_config(
    db: AsyncSession, new_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Updates centralized membership configuration in database.
    """
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "membership_config")
    )
    setting = result.scalars().first()
    cfg = DEFAULT_MEMBERSHIP_CONFIG.copy()
    cfg.update(new_config)

    raw_val = json.dumps(cfg)
    if setting:
        setting.value = raw_val
        setting.updated_at = utcnow()
    else:
        setting = SystemSettings(
            key="membership_config", value=raw_val, updated_at=utcnow()
        )
        db.add(setting)
    await db.commit()
    return cfg


def calculate_expiry(
    duration_value: int, duration_unit: str, start_time: Optional[datetime] = None
) -> datetime:
    """
    Calculates future expiry datetime given a duration value and unit (days, months, years).
    """
    base = start_time or datetime.now(timezone.utc)
    if duration_unit == "days":
        return base + timedelta(days=duration_value)
    elif duration_unit == "months":
        return base + timedelta(days=30 * duration_value)
    elif duration_unit == "years":
        return base + timedelta(days=365 * duration_value)
    # Default fallback to days
    return base + timedelta(days=duration_value)


async def check_user_membership(
    user: Optional[User], db: AsyncSession
) -> Dict[str, Any]:
    """
    Strict server-side membership authorization check.
    Returns membership entitlement status, expiration, and remaining days.
    """
    if not user:
        return {
            "has_access": False,
            "status": "unauthenticated",
            "is_admin": False,
            "activated_at": None,
            "expires_at": None,
            "days_remaining": 0,
            "membership_id": None,
        }

    # Administrators and editors automatically possess full platform access
    if user.role in ADMIN_ROLES:
        return {
            "has_access": True,
            "status": "admin_granted",
            "is_admin": True,
            "activated_at": user.created_at,
            "expires_at": None,
            "days_remaining": None,
            "membership_id": "admin",
        }

    # Query active/pending memberships for this user
    result = await db.execute(
        select(Membership)
        .where(Membership.user_id == user.id)
        .order_by(desc(Membership.created_at))
    )
    memberships = result.scalars().all()

    now = datetime.now(timezone.utc)

    # 1. Check for active membership
    for m in memberships:
        if m.status == "active":
            # Check if expired
            exp = m.expires_at
            if exp:
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp < now:
                    m.status = "expired"
                    m.updated_at = utcnow()
                    await db.commit()
                    continue

            days_rem = (
                max(0, (exp - now).days) if exp else None
            )
            return {
                "has_access": True,
                "status": "active",
                "is_admin": False,
                "activated_at": m.activated_at,
                "expires_at": m.expires_at,
                "days_remaining": days_rem,
                "membership_id": m.id,
            }

    # 2. Check for pending membership
    for m in memberships:
        if m.status == "pending":
            return {
                "has_access": False,
                "status": "pending",
                "is_admin": False,
                "activated_at": None,
                "expires_at": None,
                "days_remaining": 0,
                "membership_id": m.id,
            }

    # 3. Check for expired or revoked
    if memberships:
        latest = memberships[0]
        return {
            "has_access": False,
            "status": latest.status,  # "expired" or "revoked"
            "is_admin": False,
            "activated_at": latest.activated_at,
            "expires_at": latest.expires_at,
            "days_remaining": 0,
            "membership_id": latest.id,
        }

    # 4. No membership record at all
    return {
        "has_access": False,
        "status": "none",
        "is_admin": False,
        "activated_at": None,
        "expires_at": None,
        "days_remaining": 0,
        "membership_id": None,
    }
