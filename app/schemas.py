from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime

class ApplicationSubmit(BaseModel):
    username: Optional[str] = None
    q1_curiosity: str
    q2_awareness: str
    q3_mindset: str
    q4_reflection: str
    q5_focus: str

class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    full_name: str
    phone: Optional[str] = None
    country: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    photo_url: Optional[str] = None
    education_level: Optional[str] = None
    bio: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token (JWT)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: constr(min_length=8)

class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    status: str
    email_verified: bool
    photo_url: Optional[str] = None
    education_level: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: datetime
    meeting_link: Optional[str] = None
    registration_link: Optional[str] = None
    recording_link: Optional[str] = None

class EventOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    event_date: datetime
    meeting_link: Optional[str] = None
    registration_link: Optional[str] = None
    recording_link: Optional[str] = None
    created_at: datetime
    is_booked: Optional[bool] = False # Populated dynamically for users

    class Config:
        from_attributes = True

class EventBookingOut(BaseModel):
    id: str
    event_id: str
    user_id: str
    booked_at: datetime
    event: EventOut

    class Config:
        from_attributes = True

# --- Season & Certification System Schemas ---

class SeasonCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    number_of_sessions: Optional[int] = None
    status: str = "UPCOMING"
    min_attendance_count: int = 8
    min_participation_activities: int = 1

class SeasonUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    number_of_sessions: Optional[int] = None
    status: Optional[str] = None
    min_attendance_count: Optional[int] = None
    min_participation_activities: Optional[int] = None

class SeasonOut(SeasonCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SeasonSessionCreate(BaseModel):
    session_number: int
    session_date: datetime
    topic: str
    description: Optional[str] = None
    speaker: Optional[str] = None

class SeasonSessionOut(SeasonSessionCreate):
    id: str
    season_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AttendanceCreate(BaseModel):
    user_id: str
    session_id: str
    attendance_status: str = "PRESENT"

class AttendanceOut(BaseModel):
    id: str
    user_id: str
    season_id: str
    session_id: str
    attendance_status: str
    recorded_at: datetime

    class Config:
        from_attributes = True

class ParticipationCreate(BaseModel):
    user_id: str
    activity_type: str
    activity_description: Optional[str] = None
    activity_date: datetime

class ParticipationOut(ParticipationCreate):
    id: str
    season_id: str
    recorded_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SeasonCertificateOut(BaseModel):
    id: str
    certificate_id: str
    user_id: str
    season_id: str
    certificate_type: str
    issue_date: Optional[datetime] = None
    status: str
    pdf_url: Optional[str] = None
    verification_token: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
