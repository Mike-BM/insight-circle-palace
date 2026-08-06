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

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

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

    class Config:
        from_attributes = True
