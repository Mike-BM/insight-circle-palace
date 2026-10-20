import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import (APIRouter, BackgroundTasks, Depends, File, HTTPException,
                     Request, Response, UploadFile)
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import (generate_token, get_current_user, get_optional_user,
                      get_password_hash, hash_token, verify_password)
from app.database import get_db
from app.models import EmailVerificationToken, PasswordResetToken, Session, User
from app.schemas import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    ResetPasswordRequest,
    UserCreate,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

DEFAULT_GOOGLE_CLIENT_ID = "326628685130-e65tfg5ldhpj8vhje2ucufv9q95d8t19.apps.googleusercontent.com"


def is_secure_cookie(request: Request) -> bool:
    if os.environ.get("APP_ENV") == "production":
        return True
    proto = request.headers.get("x-forwarded-proto", "").lower()
    return proto == "https" or request.url.scheme == "https"


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if user_in.honeypot:
        # Silently drop bot submission with fake success response
        return {"message": "If the email is valid, a verification link has been sent."}

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
        country=user_in.country,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = generate_token()
    hashed_token = hash_token(token)

    verification_token = EmailVerificationToken(
        user_id=user.id,
        token_hash=hashed_token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(verification_token)
    await db.commit()

    import os

    base_url = os.environ.get("BASE_URL") or str(request.base_url).rstrip("/")
    verification_url = f"{base_url}/auth/verify-email?token={token}"
    if os.environ.get("APP_ENV") == "development":
        print(f"Verification link: {verification_url}")

    from app.services.email import send_email

    background_tasks.add_task(
        send_email,
        to_email=user.email,
        subject="Verify your Insight Circle Account",
        html_content=f"<p>Welcome to Insight Circle!</p><p>Please verify your email by clicking the link below:</p><p><a href='{verification_url}'>Verify Email</a></p>",
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
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
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
        user_agent=request.headers.get("user-agent"),
    )

    db.add(db_session)
    admin_roles = [
        "admin",
        "super_admin",
        "program_manager",
        "event_manager",
        "certificate_manager",
        "analyst",
        "editor",
        "moderator",
    ]
    if user.role in admin_roles:
        from app.models import AuditLog

        audit = AuditLog(
            admin_id=user.id,
            action="Admin Login",
            target_resource="Auth",
            target_id=user.id,
        )
        db.add(audit)
    await db.commit()

    response.set_cookie(
        key="insight_session",
        value=session_id,
        httponly=True,
        secure=is_secure_cookie(request),
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )

    return {
        "message": "Logged in successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "must_change_password": user.must_change_password,
        },
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user=Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    session_id = request.cookies.get("insight_session")
    if session_id:
        hashed = hash_token(session_id)
        result = await db.execute(
            select(Session)
            .where(Session.token_hash == hashed)
            .where(Session.revoked_at == None)
        )
        db_session = result.scalars().first()
        if db_session:
            db_session.revoked_at = datetime.now(timezone.utc)
            if current_user:
                admin_roles = [
                    "admin",
                    "super_admin",
                    "program_manager",
                    "event_manager",
                    "certificate_manager",
                    "analyst",
                    "editor",
                    "moderator",
                ]
                if current_user.role in admin_roles:
                    from app.models import AuditLog

                    audit = AuditLog(
                        admin_id=current_user.id,
                        action="Admin Logout",
                        target_resource="Auth",
                        target_id=current_user.id,
                    )
                    db.add(audit)
            await db.commit()
    response.delete_cookie(
        key="insight_session",
        httponly=True,
        secure=is_secure_cookie(request),
        samesite="lax",
        path="/",
    )
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    req_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user_email = req_data.email.lower().strip()
    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalars().first()

    generic_message = (
        "If your email is registered, you will receive password reset instructions shortly."
    )

    if not user or user.status != "active":
        return {"message": generic_message}

    raw_token = generate_token()
    hashed_token = hash_token(raw_token)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hashed_token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(reset_token)
    await db.commit()

    base_url = os.environ.get("BASE_URL") or str(request.base_url).rstrip("/")
    reset_url = f"{base_url}/static/reset-password.html?token={raw_token}"

    if os.environ.get("APP_ENV") == "development":
        print(f"Password reset link: {reset_url}")

    from app.services.email import send_email

    email_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background-color: #0b1329; color: #ffffff; border-radius: 8px;">
        <h2 style="color: #D4A345; margin-bottom: 16px;">Insight Circle Palace</h2>
        <p style="font-size: 16px; line-height: 1.5; color: #e2e8f0;">Hello {user.full_name},</p>
        <p style="font-size: 15px; line-height: 1.5; color: #cbd5e1;">We received a request to reset your password. Click the button below to set a new password. This link is valid for 1 hour.</p>
        <div style="margin: 28px 0; text-align: center;">
            <a href="{reset_url}" style="background: linear-gradient(135deg, #D4A345, #E5A93C); color: #0b1329; padding: 12px 28px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block;">Reset Password</a>
        </div>
        <p style="font-size: 13px; color: #94a3b8; line-height: 1.5;">If you did not request this, you can safely ignore this email. Your password will remain unchanged.</p>
    </div>
    """

    background_tasks.add_task(
        send_email,
        to_email=user.email,
        subject="Reset Your Insight Circle Password",
        html_content=email_html,
    )

    return {"message": generic_message}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    reset_in: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    clean_token = reset_in.token.strip()
    if not clean_token:
        raise HTTPException(status_code=400, detail="Missing reset token")

    hashed_token = hash_token(clean_token)

    result = await db.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hashed_token)
        .where(PasswordResetToken.used_at == None)
        .where(PasswordResetToken.expires_at > datetime.now(timezone.utc))
    )
    db_token = result.scalars().first()

    if not db_token:
        raise HTTPException(
            status_code=400,
            detail="The password reset link is invalid or has expired.",
        )

    user_res = await db.execute(select(User).where(User.id == db_token.user_id))
    user = user_res.scalars().first()

    if not user or user.status != "active":
        raise HTTPException(
            status_code=400, detail="Account is not active or not found."
        )

    db_token.used_at = datetime.now(timezone.utc)
    user.password_hash = get_password_hash(reset_in.new_password)
    user.must_change_password = False

    # Invalidate active sessions
    sessions_res = await db.execute(
        select(Session)
        .where(Session.user_id == user.id)
        .where(Session.revoked_at == None)
    )
    for s in sessions_res.scalars().all():
        s.revoked_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "message": "Password reset successfully. You can now log in with your new password."
    }


@router.get("/google/config")
async def google_config():
    client_id = os.environ.get("GOOGLE_CLIENT_ID", DEFAULT_GOOGLE_CLIENT_ID).strip()
    return {"client_id": client_id}


@router.post("/google")
@limiter.limit("10/minute")
async def google_auth(
    request: Request,
    response: Response,
    auth_data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    client_id = os.environ.get("GOOGLE_CLIENT_ID", DEFAULT_GOOGLE_CLIENT_ID).strip()
    token = auth_data.credential
    id_info = None

    if not client_id:
        raise HTTPException(
            status_code=500, detail="Google authentication client ID is not configured on the server."
        )

    # 1. Verify using google-auth library
    try:
        import asyncio
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
        import requests

        session = requests.Session()
        req = google_requests.Request(session=session)
        
        id_info = await asyncio.to_thread(
            id_token.verify_oauth2_token,
            token, req, client_id
        )
    except Exception as e:
        print(f"Google id_token library verification note: {e}")
        # Fallback: tokeninfo endpoint via httpx
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": token},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("aud") == client_id:
                        id_info = data
        except Exception as fetch_err:
            print(f"Fallback tokeninfo error: {fetch_err}")

    if not id_info or not id_info.get("email"):
        raise HTTPException(
            status_code=400, detail="Invalid Google authentication token"
        )

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
            status="active",
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
        user_agent=request.headers.get("user-agent"),
    )
    db.add(db_session)
    admin_roles = [
        "admin",
        "super_admin",
        "program_manager",
        "event_manager",
        "certificate_manager",
        "analyst",
        "editor",
        "moderator",
    ]
    if user.role in admin_roles:
        from app.models import AuditLog

        audit = AuditLog(
            admin_id=user.id,
            action="Admin Login",
            target_resource="Auth",
            target_id=user.id,
        )
        db.add(audit)
    await db.commit()

    response.set_cookie(
        key="insight_session",
        value=session_id,
        httponly=True,
        secure=is_secure_cookie(request),
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )

    return {
        "message": "Logged in successfully",
        "is_new_user": is_new_user,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.phone is not None:
        current_user.phone = user_update.phone
    if user_update.country is not None:
        current_user.country = user_update.country
    if user_update.education_level is not None:
        current_user.education_level = user_update.education_level
    if user_update.photo_url is not None:
        clean_photo = user_update.photo_url.strip()
        if clean_photo:
            if not (
                clean_photo.startswith("https://")
                or clean_photo.startswith("http://")
                or clean_photo.startswith("data:image/")
            ):
                raise HTTPException(
                    status_code=400, detail="Invalid photo URL format or scheme"
                )
            if len(clean_photo) > 1_000_000:
                raise HTTPException(
                    status_code=400, detail="Photo URL data is too large"
                )
            current_user.photo_url = clean_photo
        else:
            current_user.photo_url = None
    if user_update.bio is not None:
        current_user.bio = user_update.bio

    await db.commit()
    await db.refresh(current_user)
    return current_user


import os
import shutil
import uuid


@router.post("/me/photo", response_model=UserOut)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate extension
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only images are allowed."
        )

    # Content-type check (strict)
    allowed_mimes = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_mimes:
        raise HTTPException(
            status_code=400, detail="File content type must be a valid image format"
        )

    # Read file content and compress using Pillow to avoid massive DB payloads
    import base64
    import io

    from PIL import Image, ImageOps

    file_content = await file.read()

    # Limit file size to 10MB input
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

    try:
        # Open in Pillow and compress
        img = Image.open(io.BytesIO(file_content))
        # Handle camera EXIF rotation
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        ):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        # Resize thumbnail to max 400x400
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="WEBP", quality=80, method=6)
        compressed_bytes = buffer.getvalue()

        base64_encoded = base64.b64encode(compressed_bytes).decode("utf-8")
        data_url = f"data:image/webp;base64,{base64_encoded}"
    except Exception:
        # Fallback to direct raw encode if compression fails
        base64_encoded = base64.b64encode(file_content).decode("utf-8")
        data_url = f"data:{file.content_type};base64,{base64_encoded}"

    current_user.photo_url = data_url
    await db.commit()
    await db.refresh(current_user)
    return current_user
