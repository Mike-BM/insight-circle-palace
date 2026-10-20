from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, delete, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_admin, get_current_user, require_roles
from app.database import get_db
from app.models import (Application, AuditLog, Certificate, ContactEnquiry,
                        Enrollment, Event, Module, Notification, Program,
                        SystemSettings, User, utcnow)
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


class ProgramUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    is_active: Optional[bool] = None


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
@router.get("/dashboard")
async def get_dashboard(
    admin_user: User = Depends(require_roles(["analyst", "super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.status == "active")
    )
    pending_apps = await db.scalar(
        select(func.count(Application.id)).where(Application.status == "pending")
    )
    total_programs = await db.scalar(select(func.count(Program.id)))
    upcoming_events = await db.scalar(
        select(func.count(Event.id)).where(Event.event_date >= datetime.utcnow())
    )
    certs_issued = await db.scalar(select(func.count(Certificate.id)))

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
    admin_user: User = Depends(require_roles(["super_admin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    from app.services.email import send_email

    query = select(User).where(User.status == "active")
    if data.target == "members":
        query = query.where(User.role == "member")
    elif data.target == "admins":
        query = query.where(
            User.role.in_(["admin", "super_admin", "program_manager", "event_manager"])
        )

    result = await db.execute(query)
    users = result.scalars().all()

    for u in users:
        background_tasks.add_task(
            send_email, to_email=u.email, subject=data.subject, html_content=data.body
        )

    await log_audit(
        db,
        admin_user.id,
        "Email Broadcast",
        "Email",
        "all",
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
