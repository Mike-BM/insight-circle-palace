import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import get_current_admin, hash_token
from app.database import get_db
from app.models import AnalyticsEvent, Session, User

router = APIRouter(prefix="/analytics", tags=["analytics"])
limiter = Limiter(key_func=get_remote_address)


class TrackEventSchema(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    path: str = Field(..., min_length=1, max_length=500)
    metadata: Optional[Any] = None


@router.post("/track")
@limiter.limit("60/minute")
async def track_event(
    request: Request,
    event: TrackEventSchema,
    db: AsyncSession = Depends(get_db),
):
    # Try to identify the user from the auth token in cookies if present
    user_id = None
    token = request.cookies.get("insight_session") or request.cookies.get(
        "session_token"
    )
    if token:
        try:
            token_hash = hash_token(token)
            result = await db.execute(
                select(Session).where(Session.token_hash == token_hash)
            )
            session = result.scalars().first()
            if session and session.revoked_at is None:
                user_id = session.user_id
        except Exception:
            pass

    metadata_json = None
    if event.metadata:
        metadata_json = json.dumps(event.metadata)

    new_event = AnalyticsEvent(
        event_type=event.event_type,
        path=event.path,
        user_id=user_id,
        metadata_json=metadata_json,
    )
    db.add(new_event)
    await db.commit()
    return {"status": "ok"}


@router.get("/admin/stats")
async def get_analytics_stats(
    admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    # Total page views
    pv_result = await db.execute(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.event_type == "pageview"
        )
    )
    total_pageviews = pv_result.scalar() or 0

    # Unique active users (who logged an event)
    active_users_result = await db.execute(
        select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
            AnalyticsEvent.user_id.isnot(None)
        )
    )
    active_users = active_users_result.scalar() or 0

    # Calculate past 7 days breakdown
    now = datetime.now(timezone.utc)
    chart_labels = []
    chart_data = []

    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        day_label = day_start.strftime("%a")

        day_count_res = await db.execute(
            select(func.count(AnalyticsEvent.id)).where(
                AnalyticsEvent.created_at >= day_start,
                AnalyticsEvent.created_at < day_end,
            )
        )
        day_count = day_count_res.scalar() or 0
        chart_labels.append(day_label)
        chart_data.append(day_count)

    return {
        "total_pageviews": total_pageviews,
        "active_users": active_users,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
    }
