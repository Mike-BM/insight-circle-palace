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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

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
