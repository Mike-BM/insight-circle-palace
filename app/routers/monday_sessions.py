import csv
import io
import json
import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
)
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import get_current_admin, require_roles
from app.database import get_db
from app.ratelimit import limiter
from app.models import AuditLog, MondayRegistration, SystemSettings, User, utcnow
from app.schemas import MondayRegistrationCreate, MondayRegistrationOut
from app.services.email import (
    build_monday_broadcast_email,
    build_monday_registration_email,
    build_monday_reminder_email,
    send_email,
)

router = APIRouter(prefix="/api/monday-sessions", tags=["monday-sessions"])
admin_monday_router = APIRouter(
    prefix="/api/admin/monday-sessions", tags=["admin-monday-sessions"]
)


# --- Helper Methods ---


async def _get_active_monday_settings(db: AsyncSession) -> dict:
    result = await db.scalars(
        select(SystemSettings).where(SystemSettings.key == "insighters_monday")
    )
    setting = result.first()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except Exception:
            pass
    return {
        "date": "",
        "banner_short_description": "",
        "full_session_description": "",
        "poster_url": "",
        "registration_link": "",
        "is_active": False,
        "meeting_link": "",
        "recording_link": "",
    }


async def _log_monday_audit(
    db: AsyncSession,
    admin_id: str,
    action: str,
    target_resource: str = "MondaySessions",
    target_id: str = None,
    details: str = None,
):
    audit = AuditLog(
        admin_id=admin_id,
        action=action,
        target_resource=target_resource,
        target_id=target_id,
        details=details,
    )
    db.add(audit)


# --- Request Schemas ---


class MondayBroadcastActiveUsersRequest(BaseModel):
    custom_subject: Optional[str] = Field(default=None, max_length=200)
    custom_note: Optional[str] = Field(default=None, max_length=2000)


class MondayEmailRegistrantsRequest(BaseModel):
    session_date: Optional[str] = Field(default=None, max_length=100)
    subject: Optional[str] = Field(default=None, max_length=200)
    message: Optional[str] = Field(default=None, max_length=2000)


# --- Public Open Registration Endpoint ---


@router.post("/register", status_code=201)
@limiter.limit("10/minute;60/hour")
async def register_for_monday_session(
    request: Request,
    reg_in: MondayRegistrationCreate,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """
    Open public registration for Monday masterclasses.
    Accessible to ANY visitor without requiring paid membership or an existing account.
    Validates input, prevents duplicate submissions for the same session,
    and dispatches a confirmation email with calendar and meeting links.
    """
    clean_name = reg_in.full_name.strip()
    clean_email = reg_in.email.strip().lower()
    clean_session_date = reg_in.session_date.strip()
    clean_phone = (reg_in.phone or "").strip() or None
    clean_notes = (reg_in.notes or "").strip() or None

    if not clean_name or len(clean_name) < 2:
        raise HTTPException(
            status_code=400, detail="Please enter a valid full name."
        )

    if not clean_session_date or len(clean_session_date) > 100:
        raise HTTPException(
            status_code=400, detail="Please provide a valid session date."
        )

    # Anti-abuse: one address cannot be used to trigger an unlimited number of emails.
    from datetime import timedelta

    recent_regs = await db.execute(
        select(MondayRegistration.id)
        .where(MondayRegistration.email == clean_email)
        .where(MondayRegistration.registered_at > utcnow() - timedelta(hours=24))
    )
    if len(recent_regs.all()) >= 5:
        raise HTTPException(
            status_code=429,
            detail="Too many registrations for this email address. Please try again tomorrow.",
        )

    session_info = await _get_active_monday_settings(db)
    base_url = os.environ.get("BASE_URL") or str(request.base_url).rstrip("/")

    # Check for existing registration for this email & session date
    result = await db.execute(
        select(MondayRegistration)
        .where(MondayRegistration.email == clean_email)
        .where(MondayRegistration.session_date == clean_session_date)
    )
    existing = result.scalars().first()

    if existing:
        # Resend confirmation email so the attendee has the meeting link handy
        html_content = build_monday_registration_email(
            full_name=existing.full_name or clean_name,
            session_date=clean_session_date,
            session_info=session_info,
            base_url=base_url,
            is_resend=True,
        )
        topic = session_info.get("banner_short_description") or "Masterclass"
        subject = f"Your Confirmed Seat & Details: Insighters Monday ({clean_session_date}) 🎙️"

        background_tasks.add_task(
            send_email,
            to_email=clean_email,
            subject=subject,
            html_content=html_content,
        )

        return {
            "status": "already_registered",
            "message": "This email is already registered for this session. A fresh confirmation email with session access details has been dispatched to your inbox.",
            "session_date": clean_session_date,
        }

    new_reg = MondayRegistration(
        session_date=clean_session_date,
        full_name=clean_name,
        email=clean_email,
        phone=clean_phone,
        notes=clean_notes,
        status="confirmed",
        registered_at=utcnow(),
    )
    db.add(new_reg)
    await db.commit()
    await db.refresh(new_reg)

    # Dispatch confirmation email with session and calendar link
    html_content = build_monday_registration_email(
        full_name=clean_name,
        session_date=clean_session_date,
        session_info=session_info,
        base_url=base_url,
        is_resend=False,
    )
    subject = f"Confirmed: Your Seat for Insighters Monday ({clean_session_date}) 🎙️"

    background_tasks.add_task(
        send_email,
        to_email=clean_email,
        subject=subject,
        html_content=html_content,
    )

    return {
        "status": "registered",
        "message": f"Welcome aboard, {clean_name}! Your registration for Insighters Monday ({clean_session_date}) is confirmed. A confirmation email has been dispatched to your inbox.",
        "id": new_reg.id,
        "session_date": clean_session_date,
    }


# --- Admin Monday Registrations Management ---


@admin_monday_router.get(
    "/registrations", response_model=List[MondayRegistrationOut]
)
async def list_monday_registrations(
    session_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List all Monday session registrants with optional search and date filtering.
    """
    stmt = select(MondayRegistration).order_by(
        desc(MondayRegistration.registered_at)
    )

    if session_date and session_date.strip():
        stmt = stmt.where(
            MondayRegistration.session_date.ilike(f"%{session_date.strip()}%")
        )

    result = await db.execute(stmt)
    records = result.scalars().all()

    if search and search.strip():
        q = search.strip().lower()
        records = [
            r
            for r in records
            if q in r.full_name.lower()
            or q in r.email.lower()
            or (r.phone and q in r.phone.lower())
        ]

    return records


@admin_monday_router.get("/registrations/export")
async def export_monday_registrations_csv(
    session_date: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Export Monday session registrants to a downloadable CSV spreadsheet.
    """
    stmt = select(MondayRegistration).order_by(
        desc(MondayRegistration.registered_at)
    )
    if session_date and session_date.strip():
        stmt = stmt.where(
            MondayRegistration.session_date.ilike(f"%{session_date.strip()}%")
        )

    result = await db.execute(stmt)
    records = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Registration ID",
            "Full Name",
            "Email Address",
            "Phone Number",
            "Session Date",
            "Status",
            "Notes",
            "Registered At (UTC)",
        ]
    )

    for r in records:
        writer.writerow(
            [
                r.id,
                r.full_name,
                r.email,
                r.phone or "",
                r.session_date,
                r.status,
                r.notes or "",
                r.registered_at.isoformat() if r.registered_at else "",
            ]
        )

    csv_data = output.getvalue()
    filename = f"monday_registrations_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@admin_monday_router.delete("/registrations/{reg_id}")
async def delete_monday_registration(
    reg_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MondayRegistration).where(MondayRegistration.id == reg_id)
    )
    reg = result.scalars().first()
    if not reg:
        raise HTTPException(
            status_code=404, detail="Registration entry not found"
        )

    await db.delete(reg)
    await db.commit()
    return {"status": "success", "message": "Registration entry removed"}


# --- Admin Email Dispatch & Sharing Endpoints ---


@admin_monday_router.post("/broadcast-active-users")
async def broadcast_monday_to_active_users(
    request: Request,
    payload: Optional[MondayBroadcastActiveUsersRequest] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    admin_user: User = Depends(
        require_roles(["super_admin", "admin", "editor", "event_manager", "program_manager"])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Broadcasts the upcoming Insighters Monday masterclass announcement to all active users.
    """
    session_info = await _get_active_monday_settings(db)
    topic = session_info.get("banner_short_description") or "Insighters Monday Live Masterclass"
    session_date = session_info.get("date") or "Upcoming Monday · 8:00 PM EAT"
    base_url = os.environ.get("BASE_URL") or str(request.base_url).rstrip("/")

    # Query all active platform users
    result = await db.execute(select(User).where(User.status == "active"))
    active_users = result.scalars().all()

    if not active_users:
        return {"status": "ok", "sent_count": 0, "message": "No active users found."}

    custom_note = payload.custom_note if payload else None
    subject = (
        (payload.custom_subject if payload and payload.custom_subject else None)
        or f"🎙️ Upcoming Insighters Monday: {topic} ({session_date})"
    )

    html_content = build_monday_broadcast_email(
        session_info=session_info,
        custom_note=custom_note,
        base_url=base_url,
    )

    for u in active_users:
        background_tasks.add_task(
            send_email,
            to_email=u.email,
            subject=subject,
            html_content=html_content,
        )

    await _log_monday_audit(
        db,
        admin_id=admin_user.id,
        action="Broadcast to Active Users",
        target_resource="MondaySessions",
        target_id="active_users",
        details=f"Queued Insighters Monday announcement '{subject}' to {len(active_users)} active users.",
    )
    await db.commit()

    return {
        "status": "ok",
        "sent_count": len(active_users),
        "message": f"Insighters Monday announcement successfully queued for {len(active_users)} active users.",
    }


@admin_monday_router.post("/email-registrants")
async def email_monday_registrants(
    request: Request,
    payload: MondayEmailRegistrantsRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    admin_user: User = Depends(
        require_roles(["super_admin", "admin", "editor", "event_manager", "program_manager"])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Sends session reminder or live link update to all registered attendees for a session date.
    """
    session_info = await _get_active_monday_settings(db)
    base_url = os.environ.get("BASE_URL") or str(request.base_url).rstrip("/")

    stmt = select(MondayRegistration).order_by(desc(MondayRegistration.registered_at))
    if payload.session_date and payload.session_date.strip():
        stmt = stmt.where(MondayRegistration.session_date.ilike(f"%{payload.session_date.strip()}%"))

    result = await db.execute(stmt)
    registrants = result.scalars().all()

    if not registrants:
        return {"status": "ok", "sent_count": 0, "message": "No registrants matched the filter."}

    topic = session_info.get("banner_short_description") or "Insighters Monday Masterclass"
    subject = payload.subject or f"🔴 Starting Soon: Insighters Monday Access & Meeting Room ({topic})"

    # De-duplicate by email in case of multiple registrations
    seen_emails = set()
    unique_registrants = []
    for r in registrants:
        em = r.email.strip().lower()
        if em not in seen_emails:
            seen_emails.add(em)
            unique_registrants.append(r)

    for r in unique_registrants:
        html_content = build_monday_reminder_email(
            full_name=r.full_name,
            session_info=session_info,
            custom_message=payload.message,
            base_url=base_url,
        )
        background_tasks.add_task(
            send_email,
            to_email=r.email,
            subject=subject,
            html_content=html_content,
        )

    await _log_monday_audit(
        db,
        admin_id=admin_user.id,
        action="Email Registrants",
        target_resource="MondaySessions",
        target_id=payload.session_date or "all",
        details=f"Dispatched reminder email '{subject}' to {len(unique_registrants)} registrants.",
    )
    await db.commit()

    return {
        "status": "ok",
        "sent_count": len(unique_registrants),
        "message": f"Email successfully dispatched to {len(unique_registrants)} registered attendees.",
    }


@admin_monday_router.post("/registrations/{reg_id}/resend-confirmation")
async def resend_monday_registration_confirmation(
    reg_id: str,
    request: Request,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    admin_user: User = Depends(
        require_roles(["super_admin", "admin", "editor", "event_manager", "program_manager"])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually resends the confirmation and meeting access email to a specific registrant.
    """
    result = await db.execute(
        select(MondayRegistration).where(MondayRegistration.id == reg_id)
    )
    reg = result.scalars().first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration entry not found")

    session_info = await _get_active_monday_settings(db)
    base_url = os.environ.get("BASE_URL") or str(request.base_url).rstrip("/")

    html_content = build_monday_registration_email(
        full_name=reg.full_name,
        session_date=reg.session_date,
        session_info=session_info,
        base_url=base_url,
        is_resend=True,
    )
    subject = f"Your Confirmed Seat & Details: Insighters Monday ({reg.session_date}) 🎙️"

    background_tasks.add_task(
        send_email,
        to_email=reg.email,
        subject=subject,
        html_content=html_content,
    )

    await _log_monday_audit(
        db,
        admin_id=admin_user.id,
        action="Resend Confirmation",
        target_resource="MondayRegistration",
        target_id=reg.id,
        details=f"Resent confirmation email to {reg.email}.",
    )
    await db.commit()

    return {
        "status": "ok",
        "message": f"Confirmation email successfully resent to {reg.email}.",
    }
