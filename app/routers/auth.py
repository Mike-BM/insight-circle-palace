from fastapi import APIRouter, Depends, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import os

from app.database import get_db
from app.models import User, EmailVerificationToken, Session
from app.schemas import UserCreate, LoginRequest, GoogleAuthRequest, UserOut, UserUpdate
from app.auth import get_password_hash, verify_password, generate_token, hash_token, get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    user_email = user_in.email.lower().strip()
    result = await db.execute(select(User).where(User.email == user_email))
    if result.scalars().first():
        # Do not leak that email is registered
        return {"message": "If the email is valid, a verification link has been sent."}
    
    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        email=user_email,
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
    
    from app.services.email import send_email
    background_tasks.add_task(
        send_email,
        to_email=user.email,
        subject="Verify your Insight Circle Account",
        html_content=f"<p>Welcome to Insight Circle!</p><p>Please verify your email by clicking the link below:</p><p><a href='{verification_url}'>Verify Email</a></p>"
    )
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
    login_email = login_data.email.lower().strip()
    result = await db.execute(select(User).where(User.email == login_email))
    user = result.scalars().first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # if not user.email_verified:
    #     raise HTTPException(status_code=403, detail="Please verify your email first")
        
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
        secure=os.environ.get("APP_ENV") == "production", 
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

@router.get("/google/config")
async def google_config():
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    return {"client_id": client_id}

@router.post("/google")
@limiter.limit("10/minute")
async def google_auth(
    request: Request,
    response: Response,
    auth_data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    token = auth_data.credential
    id_info = None

    # 1. Verify using google-auth library
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        req = google_requests.Request()
        id_info = id_token.verify_oauth2_token(token, req, client_id if client_id else None)
    except Exception as e:
        print(f"Google id_token library verification note: {e}")
        # Fallback: tokeninfo endpoint via httpx
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": token}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if not client_id or data.get("aud") == client_id:
                        id_info = data
        except Exception as fetch_err:
            print(f"Fallback tokeninfo error: {fetch_err}")

    if not id_info or not id_info.get("email"):
        raise HTTPException(status_code=400, detail="Invalid Google authentication token")

    email = id_info["email"].lower().strip()
    full_name = id_info.get("name") or id_info.get("given_name") or email.split("@")[0]
    
    # Check if user exists in database
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    is_new_user = False

    if not user:
        random_pwd = generate_token()
        user = User(
            email=email,
            password_hash=get_password_hash(random_pwd),
            full_name=full_name,
            email_verified=True,
            status="active"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new_user = True
    else:
        if not user.email_verified:
            user.email_verified = True
        if user.status != "active":
            raise HTTPException(status_code=403, detail="Account is not active")
        await db.commit()

    # Create active session
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
        secure=os.environ.get("APP_ENV") == "production",
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    return {
        "message": "Logged in successfully",
        "is_new_user": is_new_user,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserOut)
async def update_me(user_update: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user

import shutil
import uuid
import os

@router.post("/me/photo", response_model=UserOut)
async def upload_photo(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Validate extension
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed.")
        
    # Content-type check (basic)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate a safe, random filename to prevent path traversal
    safe_filename = f"{current_user.id}_{uuid.uuid4().hex}{ext}"
    
    os.makedirs("static/uploads", exist_ok=True)
    file_path = f"static/uploads/{safe_filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    current_user.photo_url = f"/{file_path}"
    await db.commit()
    await db.refresh(current_user)
    return current_user
