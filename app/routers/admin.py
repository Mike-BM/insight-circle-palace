from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import User, Program, Event, Application, Module, Certificate, AuditLog, Notification, SystemSettings
from sqlalchemy import desc, func
from app.schemas import UserOut, EventOut
from app.auth import get_current_user, get_current_admin, require_roles

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Users ---
@router.get("/users", response_model=List[UserOut])
async def get_users(admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users

import re

class UserRoleUpdate(BaseModel):
    role: str
    status: str
    phone: Optional[str] = None
    photo_url: Optional[str] = None

@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, update_data: UserRoleUpdate, admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = update_data.role
    user.status = update_data.status
    if update_data.phone is not None:
        user.phone = re.sub(r'[^\d+\-\s()]', '', update_data.phone)
    if update_data.photo_url is not None:
        user.photo_url = update_data.photo_url
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}

# --- Programs ---
class ProgramCreate(BaseModel):
    slug: str
    title: str
    description: Optional[str] = None
    path: Optional[str] = None
    is_active: bool = True

@router.get("/programs")
async def get_programs(admin_user: User = Depends(require_roles(["program_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Program))
    programs = result.scalars().all()
    return programs

@router.post("/programs")
async def create_program(prog: ProgramCreate, admin_user: User = Depends(require_roles(["program_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    new_prog = Program(**prog.model_dump())
    db.add(new_prog)
    await db.commit()
    return new_prog

@router.put("/programs/{prog_id}")
async def update_program(prog_id: str, prog_data: ProgramCreate, admin_user: User = Depends(require_roles(["program_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Program).where(Program.id == prog_id))
    prog = result.scalars().first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    for key, value in prog_data.model_dump().items():
        setattr(prog, key, value)
    await db.commit()
    await db.refresh(prog)
    return prog

@router.delete("/programs/{prog_id}")
async def delete_program(prog_id: str, admin_user: User = Depends(require_roles(["program_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Program).where(Program.id == prog_id))
    prog = result.scalars().first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    await db.delete(prog)
    await db.commit()
    return {"message": "Program deleted"}

# --- Events ---
class EventCreateSchema(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: datetime
    meeting_link: Optional[str] = None
    registration_link: Optional[str] = None
    recording_link: Optional[str] = None

@router.get("/events")
async def get_events(admin_user: User = Depends(require_roles(["event_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event))
    events = result.scalars().all()
    return events

@router.post("/events")
async def create_event(ev: EventCreateSchema, admin_user: User = Depends(require_roles(["event_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    new_event = Event(**ev.model_dump())
    db.add(new_event)
    await db.commit()
    return new_event

@router.put("/events/{event_id}")
async def update_event(event_id: str, event_data: EventCreateSchema, admin_user: User = Depends(require_roles(["event_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    ev = result.scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    for key, value in event_data.model_dump().items():
        setattr(ev, key, value)
    await db.commit()
    await db.refresh(ev)
    return ev

@router.delete("/events/{event_id}")
async def delete_event(event_id: str, admin_user: User = Depends(require_roles(["event_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    ev = result.scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(ev)
    await db.commit()
    return {"message": "Event deleted"}

# --- Applications ---
@router.get("/applications")
async def get_applications(admin_user: User = Depends(require_roles(["program_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application))
    apps = result.scalars().all()
    return apps

class PathAssign(BaseModel):
    assigned_path: str

@router.put("/applications/{app_id}/assign-path")
async def assign_application_path(app_id: str, path_data: PathAssign, admin_user: User = Depends(require_roles(["program_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app_record = result.scalars().first()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")
    
    app_record.assigned_path = path_data.assigned_path
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
async def get_modules(prog_id: str, admin_user: User = Depends(require_roles(["program_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Module).where(Module.program_id == prog_id).order_by(Module.order))
    modules = result.scalars().all()
    return modules

@router.post("/programs/{prog_id}/modules")
async def create_module(prog_id: str, mod: ModuleCreate, admin_user: User = Depends(require_roles(["program_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    new_mod = Module(**mod.model_dump(), program_id=prog_id)
    db.add(new_mod)
    await db.commit()
    return new_mod

@router.put("/modules/{mod_id}")
async def update_module(mod_id: str, mod_data: ModuleCreate, admin_user: User = Depends(require_roles(["program_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
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
async def delete_module(mod_id: str, admin_user: User = Depends(require_roles(["program_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Module).where(Module.id == mod_id))
    mod_record = result.scalars().first()
    if not mod_record:
        raise HTTPException(status_code=404, detail="Module not found")
    await db.delete(mod_record)
    await db.commit()
    return {"message": "Module deleted"}

# --- Certificates ---
@router.get("/certificates")
async def get_certificates(admin_user: User = Depends(require_roles(["certificate_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Certificate).order_by(Certificate.issued_at.desc()))
    certs = result.scalars().all()
    return certs

@router.delete("/certificates/{cert_id}")
async def delete_certificate(cert_id: str, admin_user: User = Depends(require_roles(["certificate_manager", "super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Certificate).where(Certificate.id == cert_id))
    cert = result.scalars().first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    await db.delete(cert)
    await db.commit()
    return {"message": "Certificate deleted"}

# --- Dashboard & Analytics ---
@router.get("/dashboard")
async def get_dashboard(admin_user: User = Depends(require_roles(["analyst", "super_admin"])), db: AsyncSession = Depends(get_db)):
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(select(func.count(User.id)).where(User.status == "active"))
    pending_apps = await db.scalar(select(func.count(Application.id)).where(Application.status == "pending"))
    total_programs = await db.scalar(select(func.count(Program.id)))
    upcoming_events = await db.scalar(select(func.count(Event.id)).where(Event.event_date >= datetime.utcnow()))
    certs_issued = await db.scalar(select(func.count(Certificate.id)))

    recent_users = (await db.scalars(select(User).order_by(desc(User.created_at)).limit(5))).all()
    recent_apps = (await db.scalars(select(Application).order_by(desc(Application.submitted_at)).limit(5))).all()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "pending_applications": pending_apps,
        "total_programs": total_programs,
        "upcoming_events": upcoming_events,
        "certificates_issued": certs_issued,
        "recent_users": recent_users,
        "recent_applications": recent_apps
    }

# --- Audit Logs ---
@router.get("/audit-logs")
async def get_audit_logs(admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    logs = (await db.scalars(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(100))).all()
    return logs

# --- Settings ---
class SettingUpdate(BaseModel):
    key: str
    value: str

@router.get("/settings")
async def get_settings(admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    settings = (await db.scalars(select(SystemSettings))).all()
    return settings

@router.put("/settings")
async def update_settings(updates: List[SettingUpdate], admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    for u in updates:
        existing = await db.scalar(select(SystemSettings).where(SystemSettings.key == u.key))
        if existing:
            existing.value = u.value
        else:
            db.add(SystemSettings(key=u.key, value=u.value))
    await db.commit()
    return {"status": "ok"}

# --- Notifications ---
@router.get("/notifications")
async def get_notifications(admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    notifs = (await db.scalars(select(Notification).where(Notification.user_id == admin_user.id).order_by(desc(Notification.created_at)).limit(50))).all()
    return notifs

@router.put("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    notif = await db.scalar(select(Notification).where(Notification.id == notif_id, Notification.user_id == admin_user.id))
    if notif:
        notif.is_read = True
        await db.commit()
    return {"status": "ok"}

# --- Specific User Actions ---
@router.put("/users/{user_id}/verify")
async def verify_user(user_id: str, admin_user: User = Depends(require_roles(["super_admin"])), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")
    user.email_verified = not user.email_verified
    
    audit = AuditLog(admin_id=admin_user.id, action="Verify User Toggle", target_resource="User", target_id=user.id, details=f"Verified: {user.email_verified}")
    db.add(audit)
    
    await db.commit()
    return {"status": "ok", "email_verified": user.email_verified}

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, admin_user: User = Depends(require_roles(["super_admin"])), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")
    
    from app.auth import get_password_hash
    temp_password = "InsightCircle2026!"
    user.password_hash = get_password_hash(temp_password)
    
    audit = AuditLog(admin_id=admin_user.id, action="Reset Password", target_resource="User", target_id=user.id, details="Password reset to temporary password")
    db.add(audit)
    
    await db.commit()
    return {"status": "ok", "message": f"Password reset to: {temp_password}"}
