import uuid

from app.models import PaymentAccessRequest, ProgramEntitlement
from app.services.entitlements import grant_program_entitlement
from app.schemas import PaymentRequestApprove, PaymentRequestReject, ManualEntitlementGrant
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, case, delete, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_admin, get_current_user, require_roles
from app.database import get_db
from app.models import (Application, AuditLog, Certificate, ContactEnquiry,
                        Enrollment, Event, Lesson, LessonCompletion, Module,
                        Notification, Program, Quiz, QuizAttempt, QuizOption,
                        QuizQuestion, SystemSettings, User, utcnow)
from app.schemas import EnquiryOut, EnquiryUpdate, EventOut, UserOut


async def log_audit(
    db: AsyncSession,
    admin_id: str,
    action: str,
    target_resource: str = None,
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


router = APIRouter(prefix="/admin", tags=["admin"])


# --- Users ---
@router.get("/users", response_model=List[UserOut])
async def get_users(
    admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users


import re


class UserRoleUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    education_level: Optional[str] = None
    bio: Optional[str] = None


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    update_data: UserRoleUpdate,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    if "role" in update_dict and update_dict["role"] is not None:
        if admin_user.role != "super_admin":
            raise HTTPException(
                status_code=403, detail="Only super_admin can change user roles"
            )
        if user.id == admin_user.id and update_dict["role"] != user.role:
            raise HTTPException(
                status_code=400, detail="Users cannot update their own role"
            )
        user.role = update_dict["role"]
    if "status" in update_dict and update_dict["status"] is not None:
        if admin_user.role not in ["super_admin", "admin"]:
            raise HTTPException(
                status_code=403, detail="Only admin or super_admin can change user status"
            )
        if user.id == admin_user.id and update_dict["status"] != "active":
            raise HTTPException(
                status_code=400, detail="Cannot deactivate your own account"
            )
        user.status = update_dict["status"]
    if "full_name" in update_dict and update_dict["full_name"] is not None:
        user.full_name = update_dict["full_name"].strip()
    if "email" in update_dict and update_dict["email"] is not None:
        user.email = update_dict["email"].lower().strip()
    if "education_level" in update_dict:
        user.education_level = update_dict["education_level"]
    if "bio" in update_dict:
        user.bio = update_dict["bio"]

    if "phone" in update_dict and update_dict["phone"] is not None:
        user.phone = re.sub(r"[^\d+\-\s()]", "", update_dict["phone"])
    if "photo_url" in update_dict and update_dict["photo_url"] is not None:
        user.photo_url = update_dict["photo_url"]

    await log_audit(
        db, admin_user.id, "Update User", "User", user.id, f"Updated fields"
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: User = Depends(require_roles(["super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await log_audit(db, admin_user.id, "Delete User", "User", user.id)
    await db.commit()
    return {"message": "User deleted"}


# --- Programs ---
class ProgramCreate(BaseModel):
    slug: str
    title: str
    description: Optional[str] = None
    path: Optional[str] = None
    is_active: bool = True
    published: bool = True
    price_kes: Optional[float] = 0.0
    price_usd: Optional[float] = 0.0
    is_paid: Optional[bool] = False
    payment_instructions: Optional[str] = None


class ProgramUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    is_active: Optional[bool] = None
    published: Optional[bool] = None
    price_kes: Optional[float] = None
    price_usd: Optional[float] = None
    is_paid: Optional[bool] = None
    payment_instructions: Optional[str] = None


@router.get("/programs")
async def get_programs(
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Program))
    programs = result.scalars().all()
    return programs


@router.post("/programs")
async def create_program(
    prog: ProgramCreate,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.exc import IntegrityError

    from app.models import utcnow

    new_prog = Program(**prog.model_dump())
    new_prog.created_at = utcnow()
    new_prog.updated_at = utcnow()
    db.add(new_prog)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail="Program with this slug already exists."
        )
    await log_audit(
        db,
        admin_user.id,
        "Create Program",
        "Program",
        new_prog.id,
        f"Title: {new_prog.title}",
    )
    return new_prog


@router.put("/programs/{prog_id}")
async def update_program(
    prog_id: str,
    prog_data: ProgramUpdate,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.exc import IntegrityError

    from app.models import utcnow

    result = await db.execute(select(Program).where(Program.id == prog_id))
    prog = result.scalars().first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    for key, value in prog_data.model_dump(exclude_unset=True).items():
        setattr(prog, key, value)
    prog.updated_at = utcnow()

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail="Program with this slug already exists."
        )

    await log_audit(
        db, admin_user.id, "Update Program", "Program", prog.id, f"Updated fields"
    )
    await db.refresh(prog)
    return prog


@router.delete("/programs/{prog_id}")
async def delete_program(
    prog_id: str,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Program).where(Program.id == prog_id))
    prog = result.scalars().first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    await db.delete(prog)
    await log_audit(db, admin_user.id, "Delete Program", "Program", prog.id)
    await db.commit()
    return {"message": "Program deleted"}


# --- Events ---
class EventCreateSchema(BaseModel):
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    event_date: datetime
    meeting_link: Optional[str] = None
    registration_link: Optional[str] = None
    recording_link: Optional[str] = None
    speaker_name: Optional[str] = None
    speaker_image_url: Optional[str] = None
    speaker_bio: Optional[str] = None
    price_display: Optional[str] = None
    cover_image_url: Optional[str] = None


@router.get("/events")
async def get_events(
    admin_user: User = Depends(require_roles(["event_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event))
    events = result.scalars().all()
    return events


@router.post("/events")
async def create_event(
    ev: EventCreateSchema,
    admin_user: User = Depends(require_roles(["event_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    from app.models import utcnow

    new_event = Event(**ev.model_dump())
    new_event.created_at = utcnow()
    new_event.updated_at = utcnow()
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    await log_audit(
        db,
        admin_user.id,
        "Create Event",
        "Event",
        new_event.id,
        f"Title: {new_event.title}",
    )
    await db.commit()
    return new_event


class EventUpdateSchema(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    meeting_link: Optional[str] = None
    registration_link: Optional[str] = None
    recording_link: Optional[str] = None
    speaker_name: Optional[str] = None
    speaker_image_url: Optional[str] = None
    speaker_bio: Optional[str] = None
    price_display: Optional[str] = None
    cover_image_url: Optional[str] = None


@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    event_data: EventUpdateSchema,
    admin_user: User = Depends(require_roles(["event_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    from app.models import utcnow

    result = await db.execute(select(Event).where(Event.id == event_id))
    ev = result.scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    for key, value in event_data.model_dump(exclude_unset=True).items():
        setattr(ev, key, value)
    ev.updated_at = utcnow()
    await log_audit(
        db, admin_user.id, "Update Event", "Event", ev.id, f"Title: {ev.title}"
    )
    await db.commit()
    await db.refresh(ev)
    return ev


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    admin_user: User = Depends(require_roles(["event_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    ev = result.scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    await log_audit(
        db, admin_user.id, "Delete Event", "Event", ev.id, f"Title: {ev.title}"
    )
    await db.delete(ev)
    await db.commit()
    return {"message": "Event deleted"}


# --- Applications ---
@router.get("/applications")
async def get_applications(
    admin_user: User = Depends(
        require_roles(["program_manager", "super_admin", "admin"])
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.user))
        .order_by(desc(Application.submitted_at))
    )
    apps = result.scalars().all()
    formatted = []
    for a in apps:
        formatted.append(
            {
                "id": a.id,
                "user_id": a.user_id,
                "applicant_name": a.user.full_name if a.user else "Unknown",
                "applicant_email": a.user.email if a.user else "Unknown",
                "assigned_path": a.assigned_path,
                "status": a.status or "pending",
                "admin_notes": a.admin_notes or "",
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                "q1_curiosity": a.q1_curiosity,
                "q2_awareness": a.q2_awareness,
                "q3_mindset": a.q3_mindset,
                "q4_reflection": a.q4_reflection,
                "q5_focus": a.q5_focus,
            }
        )
    return formatted


class PathAssign(BaseModel):
    assigned_path: Optional[str] = None
    status: Optional[str] = None
    admin_notes: Optional[str] = None


@router.put("/applications/{app_id}/assign-path")
async def assign_application_path(
    app_id: str,
    path_data: PathAssign,
    admin_user: User = Depends(
        require_roles(["program_manager", "super_admin", "admin"])
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app_record = result.scalars().first()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    if path_data.assigned_path is not None:
        app_record.assigned_path = path_data.assigned_path
    if path_data.status:
        app_record.status = path_data.status
    if path_data.admin_notes is not None:
        app_record.admin_notes = path_data.admin_notes

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Review Application",
        target_resource="Application",
        target_id=app_record.id,
        details=f"Status: {app_record.status}, Path: {app_record.assigned_path}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(app_record)
    return app_record


# --- Modules ---
class ModuleCreate(BaseModel):
    title: str
    order: int
    content_url: Optional[str] = None
    description: Optional[str] = None


@router.get("/programs/{prog_id}/modules")
async def get_modules(
    prog_id: str,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Module).where(Module.program_id == prog_id).order_by(Module.order)
    )
    modules = result.scalars().all()
    return modules


@router.post("/programs/{prog_id}/modules")
async def create_module(
    prog_id: str,
    mod: ModuleCreate,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    new_mod = Module(**mod.model_dump(), program_id=prog_id)
    db.add(new_mod)
    await db.commit()
    return new_mod


@router.put("/modules/{mod_id}")
async def update_module(
    mod_id: str,
    mod_data: ModuleCreate,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Module).where(Module.id == mod_id))
    mod_record = result.scalars().first()
    if not mod_record:
        raise HTTPException(status_code=404, detail="Module not found")
    for key, value in mod_data.model_dump().items():
        setattr(mod_record, key, value)
    await db.commit()
    await db.refresh(mod_record)
    return mod_record


@router.delete("/modules/{mod_id}")
async def delete_module(
    mod_id: str,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Module).where(Module.id == mod_id))
    mod_record = result.scalars().first()
    if not mod_record:
        raise HTTPException(status_code=404, detail="Module not found")
    await db.delete(mod_record)
    await db.commit()
    return {"message": "Module deleted"}


# --- Certificates ---
class CertificateIssue(BaseModel):
    user_id: str
    program_id: str


@router.get("/certificates")
async def get_certificates(
    admin_user: User = Depends(
        require_roles(["certificate_manager", "super_admin", "admin"])
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Certificate)
        .options(selectinload(Certificate.user), selectinload(Certificate.program))
        .order_by(Certificate.issued_at.desc())
    )
    certs = result.scalars().all()
    formatted = []
    for c in certs:
        formatted.append(
            {
                "id": c.id,
                "user_id": c.user_id,
                "program_id": c.program_id,
                "certificate_number": c.certificate_number,
                "pdf_url": c.pdf_url,
                "issued_at": c.issued_at.isoformat() if c.issued_at else None,
                "verification_code": c.verification_code,
                "user_name": c.user.full_name if c.user else "Unknown User",
                "user_email": c.user.email if c.user else "Unknown",
                "program_title": c.program.title if c.program else "General Program",
            }
        )
    return formatted


@router.post("/certificates")
async def issue_certificate(
    cert_data: CertificateIssue,
    admin_user: User = Depends(
        require_roles(["certificate_manager", "super_admin", "admin"])
    ),
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.id == cert_data.user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    program = await db.scalar(select(Program).where(Program.id == cert_data.program_id))
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    enrollment = await db.scalar(
        select(Enrollment).where(
            Enrollment.user_id == cert_data.user_id,
            Enrollment.program_id == cert_data.program_id,
        )
    )
    if not enrollment:
        enrollment = Enrollment(
            user_id=cert_data.user_id,
            program_id=cert_data.program_id,
            status="completed",
            progress_percent=100,
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)
    else:
        enrollment.status = "completed"
        enrollment.progress_percent = 100
        await db.commit()

    existing_cert = await db.scalar(
        select(Certificate).where(Certificate.enrollment_id == enrollment.id)
    )
    if existing_cert:
        return {
            "status": "exists",
            "message": "Certificate already exists for this enrollment",
            "certificate_id": existing_cert.id,
            "certificate_number": existing_cert.certificate_number,
            "pdf_url": existing_cert.pdf_url,
        }

    from app.services.certificates import generate_certificate_for_enrollment

    await generate_certificate_for_enrollment(enrollment, db)

    cert = await db.scalar(
        select(Certificate).where(Certificate.enrollment_id == enrollment.id)
    )

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Issue Certificate",
        target_resource="Certificate",
        target_id=cert.id if cert else enrollment.id,
        details=f"Issued certificate {cert.certificate_number if cert else ''} to {user.email} for {program.title}",
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "ok",
        "message": "Certificate issued successfully",
        "certificate_id": cert.id if cert else None,
        "certificate_number": cert.certificate_number if cert else None,
        "pdf_url": cert.pdf_url if cert else None,
    }


@router.delete("/certificates/{cert_id}")
async def delete_certificate(
    cert_id: str,
    admin_user: User = Depends(
        require_roles(["certificate_manager", "super_admin", "admin"])
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Certificate).where(Certificate.id == cert_id))
    cert = result.scalars().first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    cert_num = cert.certificate_number
    await db.delete(cert)

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Delete Certificate",
        target_resource="Certificate",
        target_id=cert_id,
        details=f"Deleted certificate {cert_num}",
    )
    db.add(audit)
    await db.commit()
    return {"message": "Certificate deleted"}


# --- Dashboard & Analytics ---
@router.get("/dashboard/stats")

async def get_dashboard(
    admin_user: User = Depends(require_roles(["analyst", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    user_counts = (
        await db.execute(
            select(
                func.count(User.id),
                func.sum(case((User.status == "active", 1), else_=0)),
            )
        )
    ).first()
    total_users = (user_counts[0] if user_counts else 0) or 0
    active_users = (user_counts[1] if user_counts else 0) or 0

    pending_apps = (
        await db.scalar(
            select(func.count(Application.id)).where(Application.status == "pending")
        )
    ) or 0
    total_programs = (await db.scalar(select(func.count(Program.id)))) or 0
    upcoming_events = (
        await db.scalar(
            select(func.count(Event.id)).where(Event.event_date >= utcnow())
        )
    ) or 0
    certs_issued = (await db.scalar(select(func.count(Certificate.id)))) or 0

    recent_users = (
        await db.scalars(select(User).order_by(desc(User.created_at)).limit(5))
    ).all()
    recent_apps = (
        await db.scalars(
            select(Application).order_by(desc(Application.submitted_at)).limit(5)
        )
    ).all()

    return {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "pending_applications": pending_apps or 0,
        "total_programs": total_programs or 0,
        "upcoming_events": upcoming_events or 0,
        "certificates_issued": certs_issued or 0,
        "recent_users": [
            {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in recent_users
        ],
        "recent_applications": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "status": a.status,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
            }
            for a in recent_apps
        ],
    }


# --- Audit Logs ---


@router.get("/audit-logs/stats")
async def get_audit_logs_stats(
    admin_user: User = Depends(require_roles(["analyst", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    total_events = await db.scalar(select(func.count(AuditLog.id)))
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    events_today = await db.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= today)
    )
    admin_logins = await db.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.action == "Admin Login")
    )
    other_actions = (total_events or 0) - (admin_logins or 0)

    return {
        "total_events": total_events or 0,
        "events_today": events_today or 0,
        "admin_logins": admin_logins or 0,
        "other_actions": other_actions or 0,
    }


@router.get("/audit-logs")
async def get_audit_logs(
    page: int = 1,
    limit: int = 50,
    action: Optional[str] = None,
    admin_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog).options(selectinload(AuditLog.admin))

    if action:
        query = query.where(AuditLog.action == action)
    if admin_id:
        query = query.where(AuditLog.admin_id == admin_id)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.where(AuditLog.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.where(AuditLog.created_at <= end_dt)
        except ValueError:
            pass
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                AuditLog.action.ilike(search_term),
                AuditLog.target_resource.ilike(search_term),
                AuditLog.details.ilike(search_term),
                AuditLog.target_id.ilike(search_term),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)

    offset = (page - 1) * limit
    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    formatted_logs = []
    for log in logs:
        admin_name = log.admin.full_name if log.admin else "Unknown"
        admin_email = log.admin.email if log.admin else "Unknown"
        formatted_logs.append(
            {
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_name": admin_name,
                "admin_email": admin_email,
                "action": log.action,
                "target_resource": log.target_resource,
                "target_id": log.target_id,
                "details": log.details,
                "created_at": log.created_at,
            }
        )

    return {"logs": formatted_logs, "total": total_count, "page": page, "limit": limit}


# --- Settings ---
class SettingUpdate(BaseModel):
    key: str
    value: str


@router.get("/settings")
async def get_settings(
    admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    settings = (await db.scalars(select(SystemSettings))).all()
    return settings


@router.put("/settings")
async def update_settings(
    updates: List[SettingUpdate],
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    for u in updates:
        existing = await db.scalar(
            select(SystemSettings).where(SystemSettings.key == u.key)
        )
        if existing:
            existing.value = u.value
        else:
            db.add(SystemSettings(key=u.key, value=u.value))
    await db.commit()
    return {"status": "ok"}


# --- Notifications ---
@router.get("/notifications")
async def get_notifications(
    admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    notifs = (
        await db.scalars(
            select(Notification)
            .where(Notification.user_id == admin_user.id)
            .order_by(desc(Notification.created_at))
            .limit(50)
        )
    ).all()
    return notifs


@router.put("/notifications/{notif_id}/read")
async def mark_notification_read(
    notif_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    notif = await db.scalar(
        select(Notification).where(
            Notification.id == notif_id, Notification.user_id == admin_user.id
        )
    )
    if notif:
        notif.is_read = True
        await db.commit()
    return {"status": "ok"}


# --- Specific User Actions ---
@router.put("/users/{user_id}/verify")
async def verify_user(
    user_id: str,
    admin_user: User = Depends(require_roles(["super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")
    user.email_verified = not user.email_verified

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Verify User Toggle",
        target_resource="User",
        target_id=user.id,
        details=f"Verified: {user.email_verified}",
    )
    db.add(audit)

    await db.commit()
    return {"status": "ok", "email_verified": user.email_verified}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    admin_user: User = Depends(require_roles(["super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")

    import secrets
    from app.auth import get_password_hash

    temp_password = f"IC-{secrets.token_urlsafe(9)}#9"
    user.password_hash = get_password_hash(temp_password)
    user.must_change_password = True

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Reset Password",
        target_resource="User",
        target_id=user.id,
        details="Password reset to temporary password",
    )
    db.add(audit)
    await db.commit()
    return {"status": "ok", "message": f"Password reset to: {temp_password}"}


class PasswordUpdate(BaseModel):
    new_password: str


class SystemSettingsSchema(BaseModel):
    maintenance_mode: bool


import sys

app_state = sys.modules[__name__]
app_state.MAINTENANCE_MODE = False


@router.put("/settings/system")
async def update_system_settings(
    settings: SystemSettingsSchema,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    app_state.MAINTENANCE_MODE = settings.maintenance_mode
    sett = await db.scalar(
        select(SystemSettings).where(SystemSettings.key == "maintenance_mode")
    )
    if sett:
        sett.value = "true" if settings.maintenance_mode else "false"
    else:
        db.add(
            SystemSettings(
                key="maintenance_mode",
                value="true" if settings.maintenance_mode else "false",
            )
        )
    await log_audit(
        db,
        admin_user.id,
        "System Settings Update",
        "Settings",
        "system",
        f"Maintenance Mode: {settings.maintenance_mode}",
    )
    await db.commit()
    return {"status": "ok", "maintenance_mode": settings.maintenance_mode}


@router.put("/password")
async def update_password(
    data: PasswordUpdate,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if not data.new_password or len(data.new_password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters long"
        )

    from app.auth import get_password_hash

    admin_user.password_hash = get_password_hash(data.new_password)
    admin_user.must_change_password = False
    await log_audit(
        db, admin_user.id, "Update Password", "User", admin_user.id, "Password updated"
    )
    await db.commit()
    return {"status": "ok", "message": "Password updated successfully"}


class EmailBroadcast(BaseModel):
    subject: str
    body: str
    target: str = "all"  # "all", "members", "admins"


@router.post("/emails/broadcast")
async def broadcast_email(
    data: EmailBroadcast,
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(require_roles(["super_admin", "admin", "event_manager", "program_manager"])),
    db: AsyncSession = Depends(get_db),
):
    from app.services.email import send_email, wrap_email_layout

    query = select(User).where(User.status == "active")
    if data.target == "members":
        query = query.where(User.role == "member")
    elif data.target == "admins":
        query = query.where(
            User.role.in_(["admin", "super_admin", "program_manager", "event_manager"])
        )

    result = await db.execute(query)
    users = result.scalars().all()

    # Wrap in branded layout if not already a complete HTML document
    html_body = data.body
    if not ("<html" in html_body.lower() or "<body" in html_body.lower()):
        paragraphs = "".join(
            f"<p style='margin: 0 0 16px 0; font-size: 15px; line-height: 1.6; color: #e2e8f0;'>{p.strip()}</p>"
            for p in data.body.split("\n\n")
            if p.strip()
        )
        if not paragraphs:
            paragraphs = f"<p style='font-size: 15px; line-height: 1.6; color: #e2e8f0;'>{data.body}</p>"
        html_body = wrap_email_layout(data.subject, paragraphs)

    for u in users:
        background_tasks.add_task(
            send_email, to_email=u.email, subject=data.subject, html_content=html_body
        )

    await log_audit(
        db,
        admin_user.id,
        "Email Broadcast",
        "Email",
        data.target,
        f"Sent '{data.subject}' to {len(users)} users.",
    )
    await db.commit()
    return {"status": "ok", "sent_count": len(users)}


# --- Website Enquiries & Chat Messages ---


@router.get("/enquiries/stats")
async def get_enquiries_stats(
    admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    total = await db.scalar(select(func.count(ContactEnquiry.id)))
    new_count = await db.scalar(
        select(func.count(ContactEnquiry.id)).where(ContactEnquiry.status == "New")
    )
    read_count = await db.scalar(
        select(func.count(ContactEnquiry.id)).where(ContactEnquiry.status == "Read")
    )
    responded_count = await db.scalar(
        select(func.count(ContactEnquiry.id)).where(
            ContactEnquiry.status == "Responded"
        )
    )
    closed_count = await db.scalar(
        select(func.count(ContactEnquiry.id)).where(ContactEnquiry.status == "Closed")
    )
    return {
        "total": total or 0,
        "new": new_count or 0,
        "read": read_count or 0,
        "responded": responded_count or 0,
        "closed": closed_count or 0,
    }


@router.get("/enquiries")
async def get_enquiries(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(ContactEnquiry)
    if status and status.lower() != "all":
        query = query.where(ContactEnquiry.status.ilike(status))
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                ContactEnquiry.name.ilike(search_term),
                ContactEnquiry.email.ilike(search_term),
                ContactEnquiry.phone.ilike(search_term),
                ContactEnquiry.message.ilike(search_term),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)

    offset = (page - 1) * limit
    query = query.order_by(desc(ContactEnquiry.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    enquiries = result.scalars().all()

    return {
        "enquiries": [
            {
                "id": e.id,
                "name": e.name,
                "email": e.email,
                "phone": e.phone,
                "message": e.message,
                "status": e.status,
                "source": e.source,
                "session_id": e.session_id,
                "admin_notes": getattr(e, "admin_notes", None),
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            }
            for e in enquiries
        ],
        "total": total_count or 0,
        "page": page,
        "limit": limit,
    }


@router.put("/enquiries/{enquiry_id}")
async def update_enquiry(
    enquiry_id: str,
    update_data: EnquiryUpdate,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ContactEnquiry).where(ContactEnquiry.id == enquiry_id)
    )
    enquiry = result.scalars().first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    if update_data.status is not None:
        enquiry.status = update_data.status
    if update_data.admin_notes is not None:
        enquiry.admin_notes = update_data.admin_notes
    enquiry.updated_at = utcnow()

    await log_audit(
        db,
        admin_user.id,
        "Update Enquiry",
        "ContactEnquiry",
        enquiry.id,
        f"Status set to {enquiry.status}",
    )
    await db.commit()
    await db.refresh(enquiry)
    return {
        "status": "ok",
        "id": enquiry.id,
        "enquiry_status": enquiry.status,
        "admin_notes": enquiry.admin_notes,
    }


@router.delete("/enquiries/{enquiry_id}")
async def delete_enquiry(
    enquiry_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ContactEnquiry).where(ContactEnquiry.id == enquiry_id)
    )
    enquiry = result.scalars().first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    await db.delete(enquiry)
    await log_audit(
        db,
        admin_user.id,
        "Delete Enquiry",
        "ContactEnquiry",
        enquiry_id,
        f"Deleted enquiry from {enquiry.email or enquiry.name or 'Visitor'}",
    )
    await db.commit()
    return {"status": "ok", "message": "Enquiry deleted"}


# ==============================================================================
# LMS CONTENT MANAGEMENT: LESSONS, QUIZZES, & LEARNER ROSTER
# ==============================================================================

class LessonAdminCreate(BaseModel):
    title: str
    order: int = 1
    content_type: str = "text"
    content_body: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: int = 10
    is_optional: bool = False


class LessonAdminUpdate(BaseModel):
    title: Optional[str] = None
    order: Optional[int] = None
    content_type: Optional[str] = None
    content_body: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_optional: Optional[bool] = None


class LessonReorderInput(BaseModel):
    lesson_ids: List[str]


class QuizOptionAdminInput(BaseModel):
    id: Optional[str] = None
    option_text: str
    is_correct: bool = False


class QuizQuestionAdminInput(BaseModel):
    question_text: str
    explanation: Optional[str] = None
    order: int = 1
    options: List[QuizOptionAdminInput] = []


class QuizAdminCreate(BaseModel):
    program_id: str
    lesson_id: Optional[str] = None
    quiz_type: str = "lesson_quiz"  # 'lesson_quiz', 'final_assessment'
    title: str
    description: Optional[str] = None
    passing_score: int = 80
    max_retries: int = 3
    time_limit_minutes: Optional[int] = None


class QuizAdminUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    quiz_type: Optional[str] = None
    passing_score: Optional[int] = None
    max_retries: Optional[int] = None
    time_limit_minutes: Optional[int] = None


# --- Lessons CRUD ---

@router.get("/modules/{mod_id}/lessons")
async def get_module_lessons(
    mod_id: str,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all lessons in a module ordered by sequence."""
    result = await db.execute(
        select(Lesson)
        .options(selectinload(Lesson.quiz))
        .where(Lesson.module_id == mod_id)
        .order_by(Lesson.order)
    )
    lessons = result.scalars().all()
    out = []
    for l in lessons:
        out.append({
            "id": l.id,
            "module_id": l.module_id,
            "title": l.title,
            "order": l.order,
            "content_type": l.content_type,
            "content_body": l.content_body,
            "video_url": l.video_url,
            "duration_minutes": l.duration_minutes,
            "is_optional": l.is_optional,
            "created_at": l.created_at,
            "has_quiz": l.quiz is not None,
            "quiz_id": l.quiz.id if l.quiz else None,
        })
    return out


@router.post("/modules/{mod_id}/lessons")
async def create_module_lesson(
    mod_id: str,
    lesson_data: LessonAdminCreate,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Create a new lesson inside a module."""
    # Verify module exists
    mod_res = await db.execute(select(Module).where(Module.id == mod_id))
    module = mod_res.scalars().first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    new_lesson = Lesson(
        module_id=mod_id,
        title=lesson_data.title,
        order=lesson_data.order,
        content_type=lesson_data.content_type,
        content_body=lesson_data.content_body,
        video_url=lesson_data.video_url,
        duration_minutes=lesson_data.duration_minutes,
        is_optional=lesson_data.is_optional,
    )
    db.add(new_lesson)
    await db.commit()
    await db.refresh(new_lesson)

    await log_audit(
        db, admin_user.id, "create_lesson", "lessons", new_lesson.id,
        f"Created lesson '{new_lesson.title}' in module {mod_id}"
    )
    await db.commit()
    return new_lesson


@router.put("/lessons/{lesson_id}")
async def update_lesson(
    lesson_id: str,
    lesson_data: LessonAdminUpdate,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Update lesson content, order, or metadata."""
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalars().first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    for key, value in lesson_data.model_dump(exclude_unset=True).items():
        setattr(lesson, key, value)

    await db.commit()
    await db.refresh(lesson)

    await log_audit(
        db, admin_user.id, "update_lesson", "lessons", lesson.id,
        f"Updated lesson '{lesson.title}'"
    )
    await db.commit()
    return lesson


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(
    lesson_id: str,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a lesson and cascaded completions/quizzes."""
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalars().first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    title = lesson.title
    await db.delete(lesson)
    await db.commit()

    await log_audit(
        db, admin_user.id, "delete_lesson", "lessons", lesson_id,
        f"Deleted lesson '{title}'"
    )
    await db.commit()
    return {"status": "success", "message": f"Lesson '{title}' deleted"}


@router.put("/modules/{mod_id}/lessons/reorder")
async def reorder_lessons(
    mod_id: str,
    reorder_data: LessonReorderInput,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Update sequence order for multiple lessons within a module."""
    for idx, lid in enumerate(reorder_data.lesson_ids, start=1):
        res = await db.execute(
            select(Lesson).where(Lesson.id == lid, Lesson.module_id == mod_id)
        )
        lesson = res.scalars().first()
        if lesson:
            lesson.order = idx
    await db.commit()
    return {"status": "success", "reordered": len(reorder_data.lesson_ids)}


# --- Quizzes & Questions CRUD ---

@router.get("/programs/{prog_id}/quizzes")
async def get_program_quizzes(
    prog_id: str,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """List all quizzes (both lesson quizzes and final assessment) in a program."""
    result = await db.execute(
        select(Quiz)
        .options(
            selectinload(Quiz.questions).selectinload(QuizQuestion.options),
            selectinload(Quiz.lesson)
        )
        .where(Quiz.program_id == prog_id)
    )
    quizzes = result.scalars().all()
    out = []
    for q in quizzes:
        out.append({
            "id": q.id,
            "program_id": q.program_id,
            "lesson_id": q.lesson_id,
            "lesson_title": q.lesson.title if q.lesson else None,
            "quiz_type": q.quiz_type,
            "title": q.title,
            "description": q.description,
            "passing_score": q.passing_score,
            "max_retries": q.max_retries,
            "time_limit_minutes": q.time_limit_minutes,
            "question_count": len(q.questions),
            "created_at": q.created_at,
        })
    return out


@router.post("/quizzes")
async def create_quiz(
    data: QuizAdminCreate,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Create a new quiz or final assessment."""
    prog_res = await db.execute(select(Program).where(Program.id == data.program_id))
    if not prog_res.scalars().first():
        raise HTTPException(status_code=404, detail="Program not found")

    new_quiz = Quiz(
        program_id=data.program_id,
        lesson_id=data.lesson_id,
        quiz_type=data.quiz_type,
        title=data.title,
        description=data.description,
        passing_score=data.passing_score,
        max_retries=data.max_retries,
        time_limit_minutes=data.time_limit_minutes,
    )
    db.add(new_quiz)
    await db.commit()
    await db.refresh(new_quiz)

    await log_audit(
        db, admin_user.id, "create_quiz", "quizzes", new_quiz.id,
        f"Created quiz '{new_quiz.title}' type={new_quiz.quiz_type}"
    )
    await db.commit()
    return new_quiz


@router.get("/quizzes/{quiz_id}")
async def get_quiz_admin_details(
    quiz_id: str,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full quiz details including questions and options with is_correct for editing."""
    result = await db.execute(
        select(Quiz)
        .options(
            selectinload(Quiz.questions).selectinload(QuizQuestion.options)
        )
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalars().first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    sorted_questions = sorted(quiz.questions, key=lambda q: q.order)
    questions_data = []
    for q in sorted_questions:
        options_data = [
            {
                "id": opt.id,
                "option_text": opt.option_text,
                "is_correct": opt.is_correct,
            }
            for opt in q.options
        ]
        questions_data.append({
            "id": q.id,
            "question_text": q.question_text,
            "explanation": q.explanation,
            "order": q.order,
            "options": options_data,
        })

    return {
        "id": quiz.id,
        "program_id": quiz.program_id,
        "lesson_id": quiz.lesson_id,
        "quiz_type": quiz.quiz_type,
        "title": quiz.title,
        "description": quiz.description,
        "passing_score": quiz.passing_score,
        "max_retries": quiz.max_retries,
        "time_limit_minutes": quiz.time_limit_minutes,
        "questions": questions_data,
    }


@router.put("/quizzes/{quiz_id}")
async def update_quiz(
    quiz_id: str,
    data: QuizAdminUpdate,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Update quiz configuration parameters."""
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalars().first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(quiz, k, v)

    await db.commit()
    await db.refresh(quiz)

    await log_audit(
        db, admin_user.id, "update_quiz", "quizzes", quiz.id,
        f"Updated quiz '{quiz.title}'"
    )
    await db.commit()
    return quiz


@router.delete("/quizzes/{quiz_id}")
async def delete_quiz(
    quiz_id: str,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a quiz."""
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalars().first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    title = quiz.title
    await db.delete(quiz)
    await db.commit()

    await log_audit(
        db, admin_user.id, "delete_quiz", "quizzes", quiz_id,
        f"Deleted quiz '{title}'"
    )
    await db.commit()
    return {"status": "success", "message": f"Quiz '{title}' deleted"}


@router.post("/quizzes/{quiz_id}/questions")
async def add_quiz_question(
    quiz_id: str,
    data: QuizQuestionAdminInput,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Add a question and its options to a quiz."""
    quiz_res = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = quiz_res.scalars().first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    question = QuizQuestion(
        quiz_id=quiz_id,
        question_text=data.question_text,
        explanation=data.explanation,
        order=data.order,
    )
    db.add(question)
    await db.flush()  # populate question.id

    for opt in data.options:
        option = QuizOption(
            question_id=question.id,
            option_text=opt.option_text,
            is_correct=opt.is_correct,
        )
        db.add(option)

    await db.commit()
    await db.refresh(question)

    await log_audit(
        db, admin_user.id, "add_quiz_question", "quiz_questions", question.id,
        f"Added question to quiz '{quiz.title}'"
    )
    await db.commit()
    return {"status": "success", "question_id": question.id}


@router.put("/questions/{question_id}")
async def update_quiz_question(
    question_id: str,
    data: QuizQuestionAdminInput,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Update question text, explanation, order, and rebuild options."""
    res = await db.execute(
        select(QuizQuestion)
        .options(selectinload(QuizQuestion.options))
        .where(QuizQuestion.id == question_id)
    )
    question = res.scalars().first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    question.question_text = data.question_text
    question.explanation = data.explanation
    question.order = data.order

    # Remove existing options and recreate with updated payload
    for opt in list(question.options):
        await db.delete(opt)

    for opt_input in data.options:
        new_opt = QuizOption(
            question_id=question.id,
            option_text=opt_input.option_text,
            is_correct=opt_input.is_correct,
        )
        db.add(new_opt)

    await db.commit()
    return {"status": "success", "question_id": question.id}


@router.delete("/questions/{question_id}")
async def delete_quiz_question(
    question_id: str,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a question."""
    res = await db.execute(select(QuizQuestion).where(QuizQuestion.id == question_id))
    question = res.scalars().first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    await db.delete(question)
    await db.commit()
    return {"status": "success", "message": "Question deleted"}


# --- Learner Progress Roster ---

@router.get("/programs/{prog_id}/learners")
async def get_program_learners_overview(
    prog_id: str,
    admin_user: User = Depends(require_roles(["program_manager", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the real-data learner roster and progress tracking for a program.
    Includes completed lesson counts, completion percentages, last accessed lesson,
    quiz attempts, and certificate issuance records.
    """
    # Verify program
    prog_res = await db.execute(select(Program).where(Program.id == prog_id))
    program = prog_res.scalars().first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Get total required lessons count
    all_lessons_res = await db.execute(
        select(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .where(
            Module.program_id == prog_id,
            Lesson.is_optional == False  # noqa: E712
        )
    )
    total_required_lessons = all_lessons_res.scalars().all()
    total_required_count = len(total_required_lessons)

    # Get all enrollments for program with user
    enr_res = await db.execute(
        select(Enrollment)
        .options(
            selectinload(Enrollment.user),
            selectinload(Enrollment.certificate),
            selectinload(Enrollment.lesson_completions),
            selectinload(Enrollment.quiz_attempts),
        )
        .where(Enrollment.program_id == prog_id)
        .order_by(Enrollment.enrolled_at.desc())
    )
    enrollments = enr_res.scalars().all()

    learners_list = []
    for enr in enrollments:
        user = enr.user
        completed_count = len(enr.lesson_completions)
        pct = 0
        if total_required_count > 0:
            pct = min(100, int(round((completed_count / total_required_count) * 100)))
        elif enr.status == "completed":
            pct = 100

        # Last accessed lesson
        last_lesson_title = None
        if enr.last_accessed_lesson_id:
            ll_res = await db.execute(select(Lesson).where(Lesson.id == enr.last_accessed_lesson_id))
            ll = ll_res.scalars().first()
            if ll:
                last_lesson_title = ll.title

        # Final quiz attempt stats
        final_passed = False
        best_score = 0
        for att in enr.quiz_attempts:
            if att.passed:
                final_passed = True
            if att.score > best_score:
                best_score = att.score

        cert_data = None
        if enr.certificate:
            cert_data = {
                "certificate_number": enr.certificate.certificate_number,
                "verification_code": enr.certificate.verification_code,
                "issued_at": enr.certificate.issued_at,
                "pdf_url": enr.certificate.pdf_url,
            }

        learners_list.append({
            "enrollment_id": enr.id,
            "user_id": user.id if user else None,
            "full_name": user.full_name if user else "Unknown User",
            "email": user.email if user else "",
            "enrolled_at": enr.enrolled_at,
            "status": enr.status,
            "completed_lessons": completed_count,
            "total_lessons": total_required_count,
            "completion_percentage": pct,
            "last_accessed_lesson_title": last_lesson_title,
            "quiz_attempts_count": len(enr.quiz_attempts),
            "final_passed": final_passed,
            "best_quiz_score": best_score,
            "certificate": cert_data,
        })

    return {
        "program_id": program.id,
        "program_title": program.title,
        "total_required_lessons": total_required_count,
        "total_enrolled": len(enrollments),
        "learners": learners_list,
    }


# ==============================================================================
# PAYMENT ACCESS REQUESTS & ENTITLEMENTS MANAGEMENT
# ==============================================================================

@router.get("/payment-requests")
async def list_payment_requests(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(require_roles(["admin", "super_admin", "editor", "program_manager"])),
    db: AsyncSession = Depends(get_db),
):

    base_query = select(PaymentAccessRequest).options(
        selectinload(PaymentAccessRequest.user),
        selectinload(PaymentAccessRequest.program),
        selectinload(PaymentAccessRequest.approver),
    )

    if status and status.lower() != "all":
        base_query = base_query.where(PaymentAccessRequest.status == status.lower())

    base_query = base_query.order_by(PaymentAccessRequest.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(base_query)
    requests = res.scalars().all()

    # Get stats
    all_res = await db.execute(select(PaymentAccessRequest.status))
    statuses = all_res.scalars().all()
    stats = {
        "total": len(statuses),
        "pending": sum(1 for s in statuses if s == "pending"),
        "approved": sum(1 for s in statuses if s == "approved"),
        "rejected": sum(1 for s in statuses if s == "rejected"),
    }

    requests_out = []
    for r in requests:
        requests_out.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_name": r.user.full_name if r.user else "Unknown User",
            "user_email": r.user.email if r.user else "No email",
            "request_type": r.request_type,
            "program_id": r.program_id,
            "program_slug": r.program.slug if r.program else None,
            "program_title": r.program.title if r.program else None,
            "subscription_plan": r.subscription_plan,
            "amount": r.amount,
            "currency": r.currency,
            "payment_method": r.payment_method,
            "transaction_reference": r.transaction_reference,
            "notes": r.notes,
            "proof_image_url": r.proof_image_url,
            "status": r.status,
            "admin_notes": r.admin_notes,
            "approved_by": r.approver.full_name if r.approver else None,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "stats": stats,
        "requests": requests_out,
    }


@router.post("/payment-requests/{request_id}/approve")
async def approve_payment_request(
    request_id: str,
    payload: PaymentRequestApprove,
    admin_user: User = Depends(require_roles(["admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
):

    res = await db.execute(
        select(PaymentAccessRequest)
        .options(selectinload(PaymentAccessRequest.user), selectinload(PaymentAccessRequest.program))
        .where(PaymentAccessRequest.id == request_id)
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Payment request not found.")

    if req.status == "approved":
        raise HTTPException(status_code=400, detail="This payment request is already approved.")

    now = utcnow()
    req.status = "approved"
    req.approved_by = admin_user.id
    req.approved_at = now
    if payload.admin_notes:
        req.admin_notes = payload.admin_notes.strip()

    # Determine expiry days:
    # If subscription, default to 30 days if monthly, 365 if annual, unless customized
    expiry_days = payload.custom_expiry_days
    if not expiry_days and req.request_type == "subscription":
        plan = (req.subscription_plan or "").lower()
        if "annual" in plan or "year" in plan:
            expiry_days = 365
        else:
            expiry_days = 30

    # Grant Entitlement and initialize Enrollment
    entitlement = await grant_program_entitlement(
        user_id=req.user_id,
        entitlement_type=req.request_type,
        program_id=req.program_id,
        granter_id=admin_user.id,
        payment_request_id=req.id,
        expiry_days=expiry_days,
        db=db,
    )

    # Log audit entry
    audit = AuditLog(
        id=str(uuid.uuid4()),
        admin_id=admin_user.id,
        action="payment_request_approved",
        target_resource="payment_access_requests",
        target_id=req.id,
        details=f"Approved {req.request_type} access for {req.user.email if req.user else req.user_id} (Ref: {req.transaction_reference})",
        created_at=now,
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "message": "Payment request verified and access granted successfully.",
        "request_id": req.id,
        "entitlement_id": entitlement.id,
        "expires_at": entitlement.expires_at.isoformat() if entitlement.expires_at else None,
    }


@router.post("/payment-requests/{request_id}/reject")
async def reject_payment_request(
    request_id: str,
    payload: PaymentRequestReject,
    admin_user: User = Depends(require_roles(["admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
):

    res = await db.execute(
        select(PaymentAccessRequest)
        .options(selectinload(PaymentAccessRequest.user))
        .where(PaymentAccessRequest.id == request_id)
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Payment request not found.")

    now = utcnow()
    req.status = "rejected"
    req.approved_by = admin_user.id
    req.approved_at = now
    req.admin_notes = payload.admin_notes.strip()

    audit = AuditLog(
        id=str(uuid.uuid4()),
        admin_id=admin_user.id,
        action="payment_request_rejected",
        target_resource="payment_access_requests",
        target_id=req.id,
        details=f"Rejected payment for {req.user.email if req.user else req.user_id}. Reason: {req.admin_notes}",
        created_at=now,
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "message": "Payment request marked as rejected.",
        "request_id": req.id,
    }


@router.get("/entitlements")
async def list_entitlements(
    status: Optional[str] = None,
    admin_user: User = Depends(require_roles(["admin", "super_admin", "editor", "program_manager"])),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(ProgramEntitlement).options(
        selectinload(ProgramEntitlement.user),
        selectinload(ProgramEntitlement.program),
        selectinload(ProgramEntitlement.granter),
    ).order_by(ProgramEntitlement.created_at.desc())

    if status and status.lower() != "all":
        stmt = stmt.where(ProgramEntitlement.status == status.lower())

    res = await db.execute(stmt)
    entitlements = res.scalars().all()

    output = []
    for e in entitlements:
        output.append({
            "id": e.id,
            "user_id": e.user_id,
            "user_name": e.user.full_name if e.user else "Unknown User",
            "user_email": e.user.email if e.user else "No email",
            "entitlement_type": e.entitlement_type,
            "program_id": e.program_id,
            "program_title": e.program.title if e.program else ("All-Access Membership" if e.entitlement_type == "subscription" else "Unknown"),
            "status": e.status,
            "start_date": e.start_date.isoformat() if e.start_date else None,
            "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            "granted_by_name": e.granter.full_name if e.granter else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    return output


@router.post("/entitlements/manual-grant")
async def manual_grant_entitlement(
    payload: ManualEntitlementGrant,
    admin_user: User = Depends(require_roles(["admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
):

    # Verify target user
    u_res = await db.execute(select(User).where(User.id == payload.user_id))
    target_user = u_res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found.")

    ent = await grant_program_entitlement(
        user_id=payload.user_id,
        entitlement_type=payload.entitlement_type,
        program_id=payload.program_id,
        granter_id=admin_user.id,
        expiry_days=payload.expiry_days,
        db=db,
    )

    audit = AuditLog(
        id=str(uuid.uuid4()),
        admin_id=admin_user.id,
        action="manual_entitlement_granted",
        target_resource="program_entitlements",
        target_id=ent.id,
        details=f"Admin manually granted {payload.entitlement_type} access to {target_user.email}",
        created_at=utcnow(),
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "message": f"Successfully granted access to {target_user.email}",
        "entitlement_id": ent.id,
        "expires_at": ent.expires_at.isoformat() if ent.expires_at else None,
    }


@router.post("/entitlements/{entitlement_id}/revoke")
async def revoke_entitlement(
    entitlement_id: str,
    admin_user: User = Depends(require_roles(["admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
):

    res = await db.execute(
        select(ProgramEntitlement)
        .options(selectinload(ProgramEntitlement.user))
        .where(ProgramEntitlement.id == entitlement_id)
    )
    ent = res.scalar_one_or_none()
    if not ent:
        raise HTTPException(status_code=404, detail="Entitlement not found.")

    ent.status = "revoked"
    ent.updated_at = utcnow()

    audit = AuditLog(
        id=str(uuid.uuid4()),
        admin_id=admin_user.id,
        action="entitlement_revoked",
        target_resource="program_entitlements",
        target_id=ent.id,
        details=f"Revoked access for {ent.user.email if ent.user else ent.user_id}",
        created_at=utcnow(),
    )
    db.add(audit)
    await db.commit()

    return {"status": "success", "message": "Entitlement revoked successfully."}
