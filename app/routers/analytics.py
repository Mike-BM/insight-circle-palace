import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, Any
from app.database import get_db
from app.models import AnalyticsEvent, User
from app.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])

class TrackEventSchema(BaseModel):
    event_type: str
    path: str
    metadata: Optional[Any] = None

@router.post("/track")
async def track_event(
    event: TrackEventSchema, 
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Try to identify the user from the auth token in cookies if present
    user_id = None
    token = request.cookies.get("session_token")
    if token:
        try:
            # We just do a best effort to find the user session without forcing login
            from app.models import Session
            result = await db.execute(select(Session).where(Session.token_hash == token))
            session = result.scalars().first()
            if session and session.revoked_at is None:
                user_id = session.user_id
        except:
            pass

    metadata_json = None
    if event.metadata:
        metadata_json = json.dumps(event.metadata)

    new_event = AnalyticsEvent(
        event_type=event.event_type,
        path=event.path,
        user_id=user_id,
        metadata_json=metadata_json
    )
    db.add(new_event)
    await db.commit()
    return {"status": "ok"}

async def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

@router.get("/admin/stats")
async def get_analytics_stats(
    admin_user: User = Depends(get_current_admin), 
    db: AsyncSession = Depends(get_db)
):
    # Total page views
    pv_result = await db.execute(select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.event_type == 'pageview'))
    total_pageviews = pv_result.scalar() or 0

    # Unique active users (who logged an event)
    active_users_result = await db.execute(select(func.count(func.distinct(AnalyticsEvent.user_id))).where(AnalyticsEvent.user_id != None))
    active_users = active_users_result.scalar() or 0

    return {
        "total_pageviews": total_pageviews,
        "active_users": active_users
    }
