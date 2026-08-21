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
