import os
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import User, Session
from app.auth import get_password_hash, generate_token, hash_token
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

# Configure OAuth clients if environment variables are present
oauth = OAuth()

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

# Register Google if credentials present
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# Register Facebook if credentials present
FACEBOOK_CLIENT_ID = os.environ.get("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.environ.get("FACEBOOK_CLIENT_SECRET")
if FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET:
    oauth.register(
        name="facebook",
        client_id=FACEBOOK_CLIENT_ID,
        client_secret=FACEBOOK_CLIENT_SECRET,
        authorize_url="https://www.facebook.com/v15.0/dialog/oauth",
        access_token_url="https://graph.facebook.com/v15.0/oauth/access_token",
        client_kwargs={"scope": "email"},
    )


@router.get("/oauth/{provider}")
async def oauth_login(provider: str, request: Request):
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(status_code=400, detail=f"OAuth provider '{provider}' not configured")

    redirect_uri = request.url_for("oauth_callback", provider=provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/oauth/{provider}/callback", name="oauth_callback")
async def oauth_callback(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(status_code=400, detail=f"OAuth provider '{provider}' not configured")

    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to obtain access token: {e}")

    # Extract user info depending on provider
    email = None
    full_name = None

    if provider == "google":
        try:
            userinfo = await client.parse_id_token(request, token)
        except Exception:
            # Fallback: call userinfo endpoint
            userinfo = await client.get("userinfo")
            userinfo = userinfo.json()
        email = userinfo.get("email")
        full_name = userinfo.get("name") or userinfo.get("given_name")
    elif provider == "facebook":
        resp = await client.get("https://graph.facebook.com/me?fields=id,name,email", params={"access_token": token.get("access_token")})
        userinfo = resp.json()
        email = userinfo.get("email")
        full_name = userinfo.get("name")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    if not email:
        raise HTTPException(status_code=400, detail="OAuth provider did not provide an email address")

    # Find or create user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        # Create a user with a random password hash so schema requirements are satisfied
        random_pw = generate_token()
        password_hash = get_password_hash(random_pw)
        user = User(email=email, password_hash=password_hash, full_name=full_name or "")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # ensure email marked verified
        user.email_verified = True
        await db.commit()

    # Create session cookie (same as /auth/login)
    session_id = generate_token()
    hashed_session_id = hash_token(session_id)

    db_session = Session(
        user_id=user.id,
        token_hash=hashed_session_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        ip_address=None,
        user_agent=None,
    )
    db.add(db_session)
    await db.commit()

    response = RedirectResponse(url=f"{BASE_URL}/static/index.html?oauth=success")
    response.set_cookie(
        key="insight_session",
        value=session_id,
        httponly=True,
        secure=os.environ.get("APP_ENV") == "production",
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )

    return response
