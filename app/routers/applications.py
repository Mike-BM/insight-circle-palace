from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, Application
from app.schemas import ApplicationSubmit
from app.auth import get_current_user
from app.sorting import assign_path

router = APIRouter(prefix="/applications", tags=["applications"])

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
