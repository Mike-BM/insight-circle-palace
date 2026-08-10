from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import SessionRecording
import json

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

class RecordingCreate(BaseModel):
    session_id: str
    events: list

@router.post("")
async def save_recording(data: RecordingCreate, db: AsyncSession = Depends(get_db)):
    db_recording = SessionRecording(
        session_id=data.session_id,
        events_json=json.dumps(data.events)
    )
    db.add(db_recording)
    await db.commit()
    return {"status": "success"}
