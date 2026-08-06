from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import User, Application
from app.schemas import ApplicationSubmit
from app.auth import get_current_user
from app.sorting import assign_path

router = APIRouter(prefix="/applications", tags=["applications"])

@router.get("/me")
async def get_my_application(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Application)
        .where(Application.user_id == current_user.id)
        .order_by(Application.submitted_at.desc())
    )
    app_record = result.scalars().first()
    if app_record:
        return {
            "has_application": True,
            "application": {
                "id": app_record.id,
                "assigned_path": app_record.assigned_path,
                "submitted_at": app_record.submitted_at.isoformat() if app_record.submitted_at else None
            }
        }
    return {"has_application": False, "application": None}

@router.post("/submit")
async def submit_application(
    submit: ApplicationSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    path = assign_path(submit.q5_focus)
    
    app_record = Application(
        user_id=current_user.id,
        q1_curiosity=submit.q1_curiosity,
        q2_awareness=submit.q2_awareness,
        q3_mindset=submit.q3_mindset,
        q4_reflection=submit.q4_reflection,
        q5_focus=submit.q5_focus,
        assigned_path=path
    )
    
    db.add(app_record)
    await db.commit()
    
    return {"status": "success", "username": current_user.email, "path": path}

