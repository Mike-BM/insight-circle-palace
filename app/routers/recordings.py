import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import get_current_admin, get_current_user, get_optional_user
from app.database import get_db
from app.models import AuditLog, Recording, SessionRecording, User, utcnow
from app.schemas import (RecordingAdminOut, RecordingCreate as
                         VideoRecordingCreate, RecordingPlaybackOut,
                         RecordingPublicOut, RecordingUpdate)
from app.services.membership import check_user_membership
from app.services.video import (
    extract_drive_file_id,
    format_drive_embed_url,
    resolve_secure_playback_url,
)

router = APIRouter(prefix="/api/recordings", tags=["recordings"])
admin_recordings_router = APIRouter(
    prefix="/api/admin/recordings", tags=["admin-recordings"]
)


# --- Legacy/Telemetry Session Analytics Payload ---
class TelemetryCreate(BaseModel):
    session_id: str = Field(..., max_length=128)
    events: list


@router.post("")
async def save_recording_or_telemetry(
    request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Handles user session replay/telemetry payload for backward compatibility
    with frontend tracker (rrweb event json).
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "ignored"}

    events = body.get("events")
    session_id = body.get("session_id")

    if not events or not isinstance(events, list) or not session_id:
        return {"status": "ignored"}

    if len(events) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Recording payload too large (max 1000 events)",
        )

    raw_json = json.dumps(events)
    if len(raw_json) > 500_000:
        raise HTTPException(
            status_code=400,
            detail="Recording payload exceeds maximum size limit (500KB)",
        )

    clean_session_id = str(session_id).strip()[:100]
    db_recording = SessionRecording(
        session_id=clean_session_id, events_json=raw_json
    )
    db.add(db_recording)
    await db.commit()
    return {"status": "success"}


# --- Public / Member Video Recordings Endpoints ---


@router.get("", response_model=List[RecordingPublicOut])
@router.get("/", response_model=List[RecordingPublicOut])
async def list_recordings(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Public catalogue of published session recordings.
    Returns titles, dates, descriptions, thumbnails, and access status.
    Protected video embed URLs and Google Drive file IDs are NEVER leaked
    in this catalogue endpoint.
    """
    mem_status = await check_user_membership(current_user, db)
    user_has_active_membership = mem_status["has_access"]

    stmt = (
        select(Recording)
        .where(Recording.published == True)
        .order_by(desc(Recording.session_date), desc(Recording.created_at))
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    out = []
    for r in records:
        can_play = (
            r.access_requirement == "free" or user_has_active_membership
        )
        out.append(
            RecordingPublicOut(
                id=r.id,
                title=r.title,
                session_date=r.session_date,
                description=r.description,
                thumbnail_url=r.thumbnail_url,
                access_requirement=r.access_requirement,
                published=r.published,
                has_playback_access=can_play,
            )
        )
    return out


@router.get("/{recording_id}/playback", response_model=RecordingPlaybackOut)
async def get_recording_playback(
    recording_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Secure server-enforced playback authorization endpoint.
    - Public visitors can stream free sessions without requiring login.
    - Protected members-only sessions strictly require an active, verified paid membership or administrator role.
    """
    result = await db.execute(
        select(Recording).where(Recording.id == recording_id)
    )
    rec = result.scalars().first()

    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    is_admin = bool(
        current_user
        and current_user.role
        in [
            "admin",
            "super_admin",
            "editor",
            "event_manager",
            "program_manager",
        ]
    )

    if not rec.published and not is_admin:
        raise HTTPException(
            status_code=404, detail="Recording is not available"
        )

    # 1. Free sessions: accessible to all visitors and members
    if rec.access_requirement == "free":
        embed_url = await resolve_secure_playback_url(
            rec.video_source_type, rec.drive_file_id, rec.video_url
        )

        return RecordingPlaybackOut(
            id=rec.id,
            title=rec.title,
            session_date=rec.session_date,
            video_source_type=rec.video_source_type,
            drive_file_id=rec.drive_file_id,
            embed_url=embed_url,
            has_access=True,
            access_status="free",
        )

    # 2. Protected members-only sessions: strictly require authenticated user with verified membership
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in to stream members-only masterclasses.",
        )

    mem_status = await check_user_membership(current_user, db)
    if not mem_status["has_access"]:
        if mem_status.get("status") == "expired":
            raise HTTPException(
                status_code=403,
                detail="Your membership has expired. Please renew to access recordings.",
            )
        if mem_status.get("status") in ("suspended", "revoked"):
            raise HTTPException(
                status_code=403,
                detail="Your membership access has been suspended or revoked.",
            )
        raise HTTPException(
            status_code=403,
            detail="Active verified membership required to stream this recording.",
        )

    embed_url = await resolve_secure_playback_url(
        rec.video_source_type, rec.drive_file_id, rec.video_url
    )

    return RecordingPlaybackOut(
        id=rec.id,
        title=rec.title,
        session_date=rec.session_date,
        video_source_type=rec.video_source_type,
        drive_file_id=rec.drive_file_id,
        embed_url=embed_url,
        has_access=True,
        access_status=mem_status["status"],
    )


# --- Administrator Management Endpoints ---


@admin_recordings_router.get("", response_model=List[RecordingAdminOut])
@admin_recordings_router.get("/", response_model=List[RecordingAdminOut])
async def admin_list_recordings(
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Recording).order_by(
        desc(Recording.session_date), desc(Recording.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@admin_recordings_router.post(
    "", response_model=RecordingAdminOut, status_code=201
)
@admin_recordings_router.post(
    "/", response_model=RecordingAdminOut, status_code=201
)
async def admin_create_recording(
    rec_in: VideoRecordingCreate,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    clean_title = rec_in.title.strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    drive_file_id = None
    raw_drive = rec_in.drive_file_id or rec_in.drive_url_or_id
    if raw_drive:
        drive_file_id = extract_drive_file_id(raw_drive)
        if not drive_file_id and rec_in.video_source_type == "google_drive":
            raise HTTPException(
                status_code=400,
                detail="Could not extract valid Google Drive File ID. Please paste a standard sharing link or valid File ID.",
            )

    new_rec = Recording(
        title=clean_title,
        session_date=rec_in.session_date,
        description=(rec_in.description or "").strip() or None,
        video_source_type=rec_in.video_source_type,
        drive_file_id=drive_file_id,
        video_url=(rec_in.video_url or "").strip() or None,
        thumbnail_url=(rec_in.thumbnail_url or "").strip() or None,
        access_requirement=rec_in.access_requirement or "members_only",
        published=rec_in.published,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(new_rec)

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Create Recording",
        target_resource="Recording",
        target_id=new_rec.id,
        details=f"Created recording: {clean_title} (Access: {new_rec.access_requirement})",
        created_at=utcnow(),
    )
    db.add(audit)

    await db.commit()
    await db.refresh(new_rec)
    return new_rec


@admin_recordings_router.put("/{rec_id}", response_model=RecordingAdminOut)
async def admin_update_recording(
    rec_id: str,
    rec_in: RecordingUpdate,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Recording).where(Recording.id == rec_id))
    rec = result.scalars().first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    if rec_in.title is not None:
        rec.title = rec_in.title.strip()
    if rec_in.session_date is not None:
        rec.session_date = rec_in.session_date
    if rec_in.description is not None:
        rec.description = rec_in.description.strip() or None
    if rec_in.video_source_type is not None:
        rec.video_source_type = rec_in.video_source_type
    
    update_drive = rec_in.drive_file_id if rec_in.drive_file_id is not None else rec_in.drive_url_or_id
    if update_drive is not None:
        if update_drive.strip():
            extracted = extract_drive_file_id(update_drive)
            if not extracted:
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract valid Google Drive File ID.",
                )
            rec.drive_file_id = extracted
        else:
            rec.drive_file_id = None
    if rec_in.video_url is not None:
        rec.video_url = rec_in.video_url.strip() or None
    if rec_in.thumbnail_url is not None:
        rec.thumbnail_url = rec_in.thumbnail_url.strip() or None
    if rec_in.access_requirement is not None:
        rec.access_requirement = rec_in.access_requirement
    if rec_in.published is not None:
        rec.published = rec_in.published

    rec.updated_at = utcnow()

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Update Recording",
        target_resource="Recording",
        target_id=rec.id,
        details=f"Updated recording: {rec.title}",
        created_at=utcnow(),
    )
    db.add(audit)

    await db.commit()
    await db.refresh(rec)
    return rec


@admin_recordings_router.delete("/{rec_id}")
async def admin_delete_recording(
    rec_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Recording).where(Recording.id == rec_id))
    rec = result.scalars().first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    title = rec.title
    await db.delete(rec)

    audit = AuditLog(
        admin_id=admin_user.id,
        action="Delete Recording",
        target_resource="Recording",
        target_id=rec_id,
        details=f"Deleted recording: {title}",
        created_at=utcnow(),
    )
    db.add(audit)

    await db.commit()
    return {"status": "success", "message": "Recording deleted successfully"}
