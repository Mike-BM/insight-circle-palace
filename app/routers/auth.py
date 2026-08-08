from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from app.database import get_db
from app.models import User, EmailVerificationToken, Session
from app.schemas import UserCreate, LoginRequest, UserOut
from app.auth import get_password_hash, verify_password, generate_token, hash_token, get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        # Do not leak that email is registered
        return {"message": "If the email is valid, a verification link has been sent."}
    
    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        password_hash=hashed_pwd,
        full_name=user_in.full_name,
        phone=user_in.phone,
        country=user_in.country
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = generate_token()
    hashed_token = hash_token(token)
    
    verification_token = EmailVerificationToken(
        user_id=user.id,
        token_hash=hashed_token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    db.add(verification_token)
    await db.commit()
    
    import os
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    verification_url = f"{base_url}/auth/verify-email?token={token}"
    print(f"Verification link: {verification_url}")
    
    resend_key = os.environ.get("RESEND_API_KEY")
    if resend_key:
        try:
            import resend
            resend.api_key = resend_key
            resend.Emails.send({
                "from": "Insight Circle <onboarding@resend.dev>",
                "to": user.email,
                "subject": "Verify your Insight Circle Account",
                "html": f"<p>Welcome to Insight Circle!</p><p>Please verify your email by clicking the link below:</p><p><a href='{verification_url}'>Verify Email</a></p>"
            })
            print(f"Verification email sent to {user.email}")
        except Exception as e:
            print(f"Failed to send email via resend: {e}")

    return {"message": "If the email is valid, a verification link has been sent."}


@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    hashed_token = hash_token(token)
    
    result = await db.execute(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.token_hash == hashed_token)
        .where(EmailVerificationToken.used_at == None)
        .where(EmailVerificationToken.expires_at > datetime.now(timezone.utc))
    )
    db_token = result.scalars().first()
    
    if not db_token:
        return RedirectResponse(url="/static/login.html?error=invalid_token")
        
    db_token.used_at = datetime.now(timezone.utc)
    
    result = await db.execute(select(User).where(User.id == db_token.user_id))
    user = result.scalars().first()
    if user:
        user.email_verified = True
        
    await db.commit()
    return RedirectResponse(url="/static/login.html?verified=true")


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, response: Response, login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalars().first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first")
        
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account is not active")

    session_id = generate_token()
    hashed_session_id = hash_token(session_id)
    
    db_session = Session(
        user_id=user.id,
        token_hash=hashed_session_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    db.add(db_session)
    await db.commit()
    
    response.set_cookie(
        key="insight_session",
        value=session_id,
        httponly=True,
        secure=request.url.scheme == "https", 
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )
    
    return {"message": "Logged in successfully"}

@router.post("/logout")
async def logout(request: Request, response: Response, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    session_id = request.cookies.get("insight_session")
    if session_id:
        hashed = hash_token(session_id)
        result = await db.execute(
            select(Session).where(Session.token_hash == hashed).where(Session.revoked_at == None)
        )
        db_session = result.scalars().first()
        if db_session:
            db_session.revoked_at = datetime.now(timezone.utc)
            await db.commit()
    response.delete_cookie("insight_session")
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
