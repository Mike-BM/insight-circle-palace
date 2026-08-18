from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import User, Program, Event, Application
from app.schemas import UserOut, EventOut
from app.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

async def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

# --- Users ---
@router.get("/users", response_model=List[UserOut])
async def get_users(admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users

class UserRoleUpdate(BaseModel):
    role: str
    status: str

@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, update_data: UserRoleUpdate, admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = update_data.role
    user.status = update_data.status
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
async def get_programs(admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Program))
    programs = result.scalars().all()
    return programs

@router.post("/programs")
async def create_program(prog: ProgramCreate, admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    new_prog = Program(**prog.model_dump())
    db.add(new_prog)
    await db.commit()
    return new_prog

@router.delete("/programs/{prog_id}")
async def delete_program(prog_id: str, admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
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

@router.get("/events")
async def get_events(admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event))
    events = result.scalars().all()
    return events

@router.post("/events")
async def create_event(ev: EventCreateSchema, admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    new_event = Event(**ev.model_dump())
    db.add(new_event)
    await db.commit()
    return new_event

@router.delete("/events/{event_id}")
async def delete_event(event_id: str, admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    ev = result.scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(ev)
    await db.commit()
    return {"message": "Event deleted"}

# --- Applications ---
@router.get("/applications")
async def get_applications(admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application))
    apps = result.scalars().all()
    return apps

class PathAssign(BaseModel):
    assigned_path: str

@router.put("/applications/{app_id}/assign-path")
async def assign_application_path(app_id: str, path_data: PathAssign, admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app_record = result.scalars().first()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")
    
    app_record.assigned_path = path_data.assigned_path
    await db.commit()
    await db.refresh(app_record)
    return app_record
