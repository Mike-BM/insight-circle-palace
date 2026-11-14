import html
import json
import os
from typing import List, Optional

from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     Request, status)
from sqlalchemy import desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import get_current_admin, get_optional_user
from app.database import get_db
from app.models import Feedback, User, utcnow
from app.ratelimit import limiter
from app.routers.admin import log_audit
from app.schemas import (FeedbackCreate, FeedbackOut, FeedbackStatsOut,
                         FeedbackUpdate)

router = APIRouter(tags=["feedback"])

# ----------------- PUBLIC ENDPOINTS -----------------


@router.post("/api/feedback", status_code=status.HTTP_201_CREATED)
@router.post("/api/public/feedback", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute;30/hour")
async def submit_feedback(
    feedback_in: FeedbackCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Validate rating
    if not (1 <= feedback_in.rating <= 5):
        raise HTTPException(
            status_code=400, detail="Rating must be an integer between 1 and 5."
        )

    clean_message = (feedback_in.message or "").strip()
    if not clean_message:
        raise HTTPException(
            status_code=400, detail="Feedback suggestion message cannot be empty."
        )
    if len(clean_message) > 5000:
        raise HTTPException(
            status_code=400,
            detail="Feedback message is too long (maximum 5000 characters).",
        )

    # Check if user is logged in
    current_user = await get_optional_user(request, db)

    user_id = current_user.id if current_user else None
    name = (
        feedback_in.name or (current_user.full_name if current_user else "")
    ).strip() or None
    email = (
        feedback_in.email or (current_user.email if current_user else "")
    ).strip() or None

    # Process tags
    tags_str = None
    if feedback_in.tags:
        if isinstance(feedback_in.tags, list):
            tags_str = json.dumps(feedback_in.tags)
        else:
            tags_str = str(feedback_in.tags)

    category = (feedback_in.category or "General").strip()[:100]
    page_url = (feedback_in.page_url or "").strip()[:500] or None
    session_id = (feedback_in.session_id or "").strip()[:100] or None

    new_feedback = Feedback(
        user_id=user_id,
        name=name,
        email=email,
        rating=feedback_in.rating,
        category=category,
        tags=tags_str,
        message=clean_message,
        page_url=page_url,
        session_id=session_id,
        status="New",
        created_at=utcnow(),
        updated_at=utcnow(),
    )

    db.add(new_feedback)
    await db.commit()
    await db.refresh(new_feedback)

    # Notify admin via email in background
    admin_email = os.environ.get("ADMIN_EMAIL", "Insightcirclepalace@gmail.com")
    if admin_email and background_tasks:
        try:
            from app.services.email import send_email

            rating_text = f"{feedback_in.rating} / 5"
            safe_msg = html.escape(clean_message).replace("\n", "<br>")
            safe_name = html.escape(name or "Anonymous Visitor")
            safe_email = html.escape(email or "Not provided")
            email_html = f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #080E1E; color: #F4F4F5; border-radius: 12px; border: 1px solid rgba(212,163,69,0.3); overflow: hidden;">
                <div style="background: #0d1633; padding: 20px; border-bottom: 1px solid rgba(212,163,69,0.2);">
                    <h2 style="color: #D4A345; margin: 0 0 4px 0; font-size: 18px;">New Feedback Received</h2>
                    <p style="margin: 0; font-size: 12px; color: #94A3B8;">Insight Circle Palace Management</p>
                </div>
                <div style="padding: 20px;">
                    <div style="background: rgba(255,255,255,0.04); border-radius: 8px; padding: 14px; margin-bottom: 18px;">
                        <p style="margin: 0 0 6px 0; font-size: 15px;"><strong>Rating:</strong> {rating_text}</p>
                        <p style="margin: 0 0 6px 0; font-size: 13px;"><strong>Category:</strong> <span style="color: #D4A345;">{html.escape(category)}</span></p>
                        <p style="margin: 0 0 6px 0; font-size: 13px;"><strong>From:</strong> {safe_name} ({safe_email})</p>
                        {f'<p style="margin: 0; font-size: 13px;"><strong>Tags:</strong> {html.escape(tags_str)}</p>' if tags_str else ''}
                    </div>
                    <div style="margin-bottom: 20px;">
                        <h4 style="color: #D4A345; margin: 0 0 8px 0; font-size: 13px; text-transform: uppercase;">Message / Details:</h4>
                        <div style="background: #0f1a36; border-left: 3px solid #D4A345; padding: 12px 16px; border-radius: 4px; line-height: 1.5; font-size: 13px; color: #E2E8F0;">
                            {safe_msg}
                        </div>
                    </div>
                    <div style="text-align: center; padding-top: 8px;">
                        <a href="{os.environ.get('BASE_URL', 'https://insightcirclepalace.org').rstrip('/')}/admin/dashboard" style="display: inline-block; padding: 10px 20px; background: #D4A345; color: #080E1E; font-weight: bold; border-radius: 6px; text-decoration: none; font-size: 13px;">Open Admin Dashboard</a>
                    </div>
                </div>
            </div>
            """
            background_tasks.add_task(
                send_email,
                to_email=admin_email,
                subject=f"New Feedback [{category}] - Rating {feedback_in.rating}/5 from {safe_name}",
                html_content=email_html,
            )
        except Exception:
            pass

    return {
        "status": "ok",
        "id": new_feedback.id,
        "message": "Thank you. Your feedback has been received.",
    }


# ----------------- PUBLIC RATING ENDPOINT -----------------
# Public can access aggregate score/average, but individual feedback comments are strictly private.
@router.get("/api/public/rating")
async def get_public_rating(db: AsyncSession = Depends(get_db)):
    avg_rating_val = await db.scalar(select(func.avg(Feedback.rating)))
    total_ratings = await db.scalar(select(func.count(Feedback.id))) or 0
    avg_rating = round(float(avg_rating_val), 1) if avg_rating_val is not None else 4.9
    return {"average_rating": avg_rating, "total_ratings": total_ratings}


# ----------------- ADMIN ENDPOINTS -----------------


@router.get("/admin/feedback/stats", response_model=FeedbackStatsOut)
async def get_feedback_stats(
    admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    total = await db.scalar(select(func.count(Feedback.id))) or 0
    avg_rating_val = await db.scalar(select(func.avg(Feedback.rating)))
    avg_rating = round(float(avg_rating_val), 2) if avg_rating_val is not None else 5.0
    new_count = (
        await db.scalar(select(func.count(Feedback.id)).where(Feedback.status == "New"))
        or 0
    )
    reviewed_count = (
        await db.scalar(
            select(func.count(Feedback.id)).where(Feedback.status == "Reviewed")
        )
        or 0
    )

    # Distribution 1 to 5
    breakdown = {}
    for r in range(1, 6):
        cnt = (
            await db.scalar(select(func.count(Feedback.id)).where(Feedback.rating == r))
            or 0
        )
        breakdown[str(r)] = cnt

    return {
        "total": total,
        "average_rating": avg_rating,
        "new_count": new_count,
        "reviewed_count": reviewed_count,
        "ratings_breakdown": breakdown,
    }


@router.get("/admin/feedback")
async def get_feedback_list(
    page: int = 1,
    limit: int = 25,
    status: Optional[str] = None,
    rating: Optional[int] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Feedback)

    if status and status.lower() != "all":
        query = query.where(Feedback.status.ilike(status))

    if rating and rating in (1, 2, 3, 4, 5):
        query = query.where(Feedback.rating == rating)

    if category and category.lower() != "all":
        query = query.where(Feedback.category.ilike(category))

    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                Feedback.name.ilike(term),
                Feedback.email.ilike(term),
                Feedback.message.ilike(term),
                Feedback.tags.ilike(term),
                Feedback.category.ilike(term),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query) or 0

    offset = (page - 1) * limit
    query = query.order_by(desc(Feedback.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    feedbacks = result.scalars().all()

    items = []
    for f in feedbacks:
        tags_list = []
        if f.tags:
            try:
                tags_list = json.loads(f.tags)
            except Exception:
                tags_list = [t.strip() for t in f.tags.split(",") if t.strip()]

        items.append(
            {
                "id": f.id,
                "user_id": f.user_id,
                "name": f.name or "Anonymous User",
                "email": f.email or "Not provided",
                "rating": f.rating,
                "category": f.category,
                "tags": tags_list,
                "message": f.message,
                "page_url": f.page_url,
                "session_id": f.session_id,
                "status": f.status,
                "admin_notes": f.admin_notes,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "updated_at": f.updated_at.isoformat() if f.updated_at else None,
            }
        )

    return {"feedback": items, "total": total_count, "page": page, "limit": limit}


@router.put("/admin/feedback/{feedback_id}")
async def update_feedback(
    feedback_id: str,
    update_data: FeedbackUpdate,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Feedback entry not found")

    if update_data.status is not None:
        item.status = update_data.status
    if update_data.admin_notes is not None:
        item.admin_notes = update_data.admin_notes
    item.updated_at = utcnow()

    await log_audit(
        db,
        admin_user.id,
        "Update Feedback",
        "Feedback",
        item.id,
        f"Status: {item.status}",
    )
    await db.commit()
    await db.refresh(item)

    return {
        "status": "ok",
        "id": item.id,
        "feedback_status": item.status,
        "admin_notes": item.admin_notes,
    }


@router.delete("/admin/feedback/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Feedback entry not found")

    await log_audit(
        db,
        admin_user.id,
        "Delete Feedback",
        "Feedback",
        item.id,
        f"Deleted feedback from {item.email or item.name or 'Anonymous'}",
    )
    await db.delete(item)
    await db.commit()

    return {"status": "ok", "message": "Feedback entry deleted successfully"}
