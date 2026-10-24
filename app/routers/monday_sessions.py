import csv
import io
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import get_current_admin
from app.database import get_db
from app.models import AuditLog, MondayRegistration, User, utcnow
from app.schemas import MondayRegistrationCreate, MondayRegistrationOut

router = APIRouter(prefix="/api/monday-sessions", tags=["monday-sessions"])
admin_monday_router = APIRouter(
    prefix="/api/admin/monday-sessions", tags=["admin-monday-sessions"]
)
limiter = Limiter(key_func=get_remote_address)


# --- Public Open Registration Endpoint ---


@router.post("/register", status_code=201)
@limiter.limit("10/minute")
async def register_for_monday_session(
    request: Request,
    reg_in: MondayRegistrationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Open public registration for Monday masterclasses.
    Accessible to ANY visitor without requiring paid membership or an existing account.
    Validates input and prevents duplicate submissions for the same session.
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

    if not clean_session_date:
        raise HTTPException(
            status_code=400, detail="Session date cannot be empty."
        )

    # Check for existing registration for this email & session date
    result = await db.execute(
        select(MondayRegistration)
        .where(MondayRegistration.email == clean_email)
        .where(MondayRegistration.session_date == clean_session_date)
    )
    existing = result.scalars().first()

    if existing:
        return {
            "status": "already_registered",
            "message": "This email is already registered for this session. A reminder will be sent before the event.",
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

    return {
        "status": "registered",
        "message": f"Welcome aboard, {clean_name}! Your registration for Insighters Monday ({clean_session_date}) is confirmed.",
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
