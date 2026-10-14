import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SessionRecording

router = APIRouter(prefix="/api/recordings", tags=["recordings"])


class RecordingCreate(BaseModel):
    session_id: str = Field(..., max_length=128)
    events: list


@router.post("")
async def save_recording(data: RecordingCreate, db: AsyncSession = Depends(get_db)):
    if not data.events or not isinstance(data.events, list):
        return {"status": "ignored"}

    # Cap maximum number of events to prevent DoS
    if len(data.events) > 1000:
        raise HTTPException(
            status_code=400, detail="Recording payload too large (max 1000 events)"
        )

    raw_json = json.dumps(data.events)
    # Cap serialized JSON payload to 500KB
    if len(raw_json) > 500_000:
        raise HTTPException(
            status_code=400,
            detail="Recording payload exceeds maximum size limit (500KB)",
        )

    clean_session_id = data.session_id.strip()[:100]
    db_recording = SessionRecording(
        session_id=clean_session_id, events_json=raw_json
    )
    db.add(db_recording)
    await db.commit()
    return {"status": "success"}
