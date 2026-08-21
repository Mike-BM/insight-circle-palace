import re

with open('app/routers/admin.py', 'r') as f:
    content = f.read()

# Replace imports
content = re.sub(
    r'from app\.models import .*',
    'from app.models import User, Program, Event, Application, Module, Certificate, AuditLog, Notification, SystemSettings\nfrom sqlalchemy import desc, func',
    content
)
content = re.sub(
    r'from app\.auth import get_current_user',
    'from app.auth import get_current_user, get_current_admin, require_roles',
    content
)

# Remove the local get_current_admin
content = re.sub(
    r'async def get_current_admin.*?\n    return current_user\n',
    '',
    content,
    flags=re.DOTALL
)

# Replace roles for endpoints
content = re.sub(r'(def get_programs.*?Depends\()get_current_admin(\))', r'\1require_roles(["program_manager", "super_admin"])\2', content)
content = re.sub(r'(def create_program.*?Depends\()get_current_admin(\))', r'\1require_roles(["program_manager", "super_admin"])\2', content)
content = re.sub(r'(def update_program.*?Depends\()get_current_admin(\))', r'\1require_roles(["program_manager", "super_admin"])\2', content)
content = re.sub(r'(def delete_program.*?Depends\()get_current_admin(\))', r'\1require_roles(["program_manager", "super_admin"])\2', content)

content = re.sub(r'(def get_events.*?Depends\()get_current_admin(\))', r'\1require_roles(["event_manager", "super_admin"])\2', content)
content = re.sub(r'(def create_event.*?Depends\()get_current_admin(\))', r'\1require_roles(["event_manager", "super_admin"])\2', content)
content = re.sub(r'(def update_event.*?Depends\()get_current_admin(\))', r'\1require_roles(["event_manager", "super_admin"])\2', content)
content = re.sub(r'(def delete_event.*?Depends\()get_current_admin(\))', r'\1require_roles(["event_manager", "super_admin"])\2', content)

content = re.sub(r'(def get_applications.*?Depends\()get_current_admin(\))', r'\1require_roles(["program_manager", "super_admin"])\2', content)
content = re.sub(r'(def assign_application_path.*?Depends\()get_current_admin(\))', r'\1require_roles(["program_manager", "super_admin"])\2', content)

content = re.sub(r'(def get_modules.*?Depends\()get_current_admin(\))', r'\1require_roles(["program_manager", "super_admin"])\2', content)
content = re.sub(r'(def create_module.*?Depends\()get_current_admin(\))', r'\1require_roles(["program_manager", "super_admin"])\2', content)
content = re.sub(r'(def update_module.*?Depends\()get_current_admin(\))', r'\1require_roles(["program_manager", "super_admin"])\2', content)
content = re.sub(r'(def delete_module.*?Depends\()get_current_admin(\))', r'\1require_roles(["program_manager", "super_admin"])\2', content)

content = re.sub(r'(def get_certificates.*?Depends\()get_current_admin(\))', r'\1require_roles(["certificate_manager", "super_admin"])\2', content)
content = re.sub(r'(def delete_certificate.*?Depends\()get_current_admin(\))', r'\1require_roles(["certificate_manager", "super_admin"])\2', content)


# Add new endpoints at the end
new_endpoints = """
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
"""

with open('app/routers/admin.py', 'w') as f:
    f.write(content + new_endpoints)
