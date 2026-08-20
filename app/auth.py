import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import Session, User
import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode('utf-8')[:72]
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    session_id = request.cookies.get("insight_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    hashed_session_id = hash_token(session_id)
    
    # Lookup session
    result = await db.execute(
        select(Session)
        .where(Session.token_hash == hashed_session_id)
        .where(Session.revoked_at == None)
        .where(Session.expires_at > datetime.now(timezone.utc))
    )
    db_session = result.scalars().first()
    
    if not db_session:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    
    # Lookup user
    result = await db.execute(select(User).where(User.id == db_session.user_id))
    user = result.scalars().first()
    
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="User account is inactive or deleted")
        
    return user

async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    admin_roles = ["admin", "super_admin", "program_manager", "event_manager", "certificate_manager", "analyst"]
    if current_user.role not in admin_roles:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

def require_roles(allowed_roles: list[str]):
    async def role_checker(current_user: User = Depends(get_current_admin)) -> User:
        if current_user.role == "super_admin" or current_user.role == "admin":
            return current_user
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Role not authorized for this section")
        return current_user
    return role_checker

async def get_optional_user(request: Request, db: AsyncSession = Depends(get_db)):
    session_id = request.cookies.get("insight_session")
    if not session_id:
        return None
    
    hashed_session_id = hash_token(session_id)
    
    # Lookup session
    result = await db.execute(
        select(Session)
        .where(Session.token_hash == hashed_session_id)
        .where(Session.revoked_at == None)
        .where(Session.expires_at > datetime.now(timezone.utc))
    )
    db_session = result.scalars().first()
    
    if not db_session:
        return None
    
    # Lookup user
    result = await db.execute(select(User).where(User.id == db_session.user_id))
    user = result.scalars().first()
    
    if not user or user.status != "active":
        return None
        
    return user

