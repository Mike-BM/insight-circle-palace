from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class ApplicationSubmit(BaseModel):
    q1_curiosity: str
    q2_awareness: str
    q3_mindset: str
    q4_reflection: str
    q5_focus: str

class ApplicationRecord(BaseModel):
    id: str
    answers: ApplicationSubmit
    path: str
    status: str = "pending"
    unlock_at: datetime
    submitted_at: datetime
    
    @classmethod
    def create(cls, answers: ApplicationSubmit, path: str, unlock_at: datetime) -> "ApplicationRecord":
        return cls(
            id=str(uuid.uuid4()),
            answers=answers,
            path=path,
            unlock_at=unlock_at,
            submitted_at=datetime.utcnow()
        )
