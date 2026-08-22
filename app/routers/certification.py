from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from app.database import get_db
from app.models import Season, SeasonSession, Attendance, Participation, SeasonCertificate, User
from app.auth import get_current_admin, get_optional_user

router = APIRouter(prefix="/seasons", tags=["certification"])

@router.post("/{season_id}/certification/evaluate")
async def evaluate_season(
    season_id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    # Fetch Season
    result = await db.execute(select(Season).where(Season.id == season_id))
    season = result.scalars().first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")

    # Fetch total sessions
    session_res = await db.execute(select(SeasonSession).where(SeasonSession.season_id == season_id))
    total_sessions = len(session_res.scalars().all())

    # Get all users who have attended at least once
    attendance_res = await db.execute(select(Attendance).where(Attendance.season_id == season_id))
    attendances = attendance_res.scalars().all()

    # Get all participations
    part_res = await db.execute(select(Participation).where(Participation.season_id == season_id))
    participations = part_res.scalars().all()

    # Process metrics per user
    user_metrics = {}
    for a in attendances:
        if a.attendance_status == "PRESENT":
            if a.user_id not in user_metrics:
                user_metrics[a.user_id] = {"attendance_count": 0, "participation_count": 0}
            user_metrics[a.user_id]["attendance_count"] += 1

    for p in participations:
        if p.user_id in user_metrics:
            user_metrics[p.user_id]["participation_count"] += 1

    # Evaluate
    results = []
    for user_id, metrics in user_metrics.items():
        att_count = metrics["attendance_count"]
        part_count = metrics["participation_count"]
        
        completion_eligible = (
            att_count >= (season.min_attendance_count or 0) and
            part_count >= (season.min_participation_activities or 0)
        )

        rec_cert = "Completion" if completion_eligible else "Participation"

        results.append({
            "user_id": user_id,
            "attendance": f"{att_count}/{total_sessions}",
            "participation": part_count > 0,
            "completion_eligible": completion_eligible,
            "recommended_certificate": rec_cert
        })

    return {"season_id": season_id, "evaluations": results}
