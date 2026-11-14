import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import get_optional_user, require_roles
from app.models import User
from app.database import Base, engine, get_db
from app.ratelimit import limiter
from app.routers import (admin, analytics, applications, assignments, auth, certificates, payments,
                         quizzes,
                         certification, events, feedback, memberships, monday_sessions, programs, recordings,
                         seasons, merchandise, mpesa, stripe)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created on startup
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            is_sqlite = engine.url.drivername.startswith("sqlite")
            for stmt in [
                "ALTER TABLE applications ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'pending';",
                "ALTER TABLE applications ADD COLUMN IF NOT EXISTS admin_notes TEXT;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active';",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS path VARCHAR;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS start_date TIMESTAMP WITH TIME ZONE;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS end_date TIMESTAMP WITH TIME ZONE;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS capacity INTEGER;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS published BOOLEAN NOT NULL DEFAULT TRUE;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS price_kes FLOAT DEFAULT 0.0;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS price_usd FLOAT DEFAULT 0.0;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS is_paid BOOLEAN DEFAULT TRUE;",
                "ALTER TABLE programs ADD COLUMN IF NOT EXISTS payment_instructions TEXT;",
                "CREATE TABLE IF NOT EXISTS payment_access_requests (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, request_type VARCHAR(20) NOT NULL DEFAULT 'program', program_id VARCHAR(36), subscription_plan VARCHAR(50), amount FLOAT DEFAULT 0.0, currency VARCHAR(10) NOT NULL DEFAULT 'KES', payment_method VARCHAR(30) NOT NULL DEFAULT 'mpesa_manual', transaction_reference VARCHAR(100) NOT NULL, notes TEXT, proof_image_url VARCHAR(500), status VARCHAR(20) NOT NULL DEFAULT 'pending', admin_notes TEXT, approved_by VARCHAR(36), approved_at TIMESTAMP WITH TIME ZONE, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
                "CREATE TABLE IF NOT EXISTS program_entitlements (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, entitlement_type VARCHAR(20) NOT NULL DEFAULT 'program', program_id VARCHAR(36), payment_request_id VARCHAR(36), status VARCHAR(20) NOT NULL DEFAULT 'active', start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP WITH TIME ZONE, granted_by VARCHAR(36), created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",

                "ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS last_accessed_lesson_id VARCHAR(36);",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS cover_image_url VARCHAR;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS speaker_name VARCHAR;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS speaker_bio TEXT;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS speaker_image_url VARCHAR;",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS price_display VARCHAR;",
                "CREATE TABLE IF NOT EXISTS contact_enquiries (id VARCHAR(36) PRIMARY KEY, name VARCHAR, email VARCHAR, phone VARCHAR, message TEXT NOT NULL, status VARCHAR NOT NULL DEFAULT 'New', source VARCHAR NOT NULL DEFAULT 'chat_widget', session_id VARCHAR, admin_notes TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
                "CREATE TABLE IF NOT EXISTS feedback (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36), name VARCHAR, email VARCHAR, rating INTEGER NOT NULL DEFAULT 5, category VARCHAR NOT NULL DEFAULT 'General', tags TEXT, message TEXT NOT NULL, page_url VARCHAR, session_id VARCHAR, status VARCHAR NOT NULL DEFAULT 'New', admin_notes TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
                "CREATE TABLE IF NOT EXISTS recordings (id VARCHAR(36) PRIMARY KEY, title VARCHAR NOT NULL, session_date TIMESTAMP WITH TIME ZONE, description TEXT, video_source_type VARCHAR NOT NULL DEFAULT 'google_drive', drive_file_id VARCHAR, video_url VARCHAR, thumbnail_url VARCHAR, access_requirement VARCHAR NOT NULL DEFAULT 'members_only', published BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
                "CREATE TABLE IF NOT EXISTS monday_registrations (id VARCHAR(36) PRIMARY KEY, session_date VARCHAR NOT NULL, full_name VARCHAR NOT NULL, email VARCHAR NOT NULL, phone VARCHAR, notes TEXT, status VARCHAR NOT NULL DEFAULT 'confirmed', registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
                "CREATE TABLE IF NOT EXISTS memberships (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL REFERENCES users(id), status VARCHAR NOT NULL DEFAULT 'pending', fee_paid FLOAT, currency VARCHAR NOT NULL DEFAULT 'KES', activated_at TIMESTAMP WITH TIME ZONE, expires_at TIMESTAMP WITH TIME ZONE, granted_by VARCHAR(36) REFERENCES users(id), notes TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
                "CREATE TABLE IF NOT EXISTS payment_submissions (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL REFERENCES users(id), membership_id VARCHAR(36) REFERENCES memberships(id), transaction_reference VARCHAR NOT NULL UNIQUE, payment_method VARCHAR NOT NULL DEFAULT 'mpesa', amount FLOAT NOT NULL, currency VARCHAR NOT NULL DEFAULT 'KES', payer_name VARCHAR, payer_phone VARCHAR, status VARCHAR NOT NULL DEFAULT 'pending', submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, verified_at TIMESTAMP WITH TIME ZONE, verified_by VARCHAR(36) REFERENCES users(id), admin_notes TEXT);",
                "CREATE TABLE IF NOT EXISTS mpesa_transactions (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL REFERENCES users(id), phone_number VARCHAR(20) NOT NULL, amount FLOAT NOT NULL DEFAULT 250.0, currency VARCHAR(10) NOT NULL DEFAULT 'KES', merchant_request_id VARCHAR(100), checkout_request_id VARCHAR(100) NOT NULL UNIQUE, status VARCHAR(30) NOT NULL DEFAULT 'initiated', mpesa_receipt_number VARCHAR(100) UNIQUE, result_code INTEGER, result_desc TEXT, transaction_date TIMESTAMP WITH TIME ZONE, raw_callback TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
                "CREATE INDEX IF NOT EXISTS ix_mpesa_checkout_id ON mpesa_transactions(checkout_request_id);",
                "CREATE INDEX IF NOT EXISTS ix_mpesa_receipt ON mpesa_transactions(mpesa_receipt_number);",
                "CREATE INDEX IF NOT EXISTS ix_mpesa_user_id ON mpesa_transactions(user_id);",
                "CREATE TABLE IF NOT EXISTS merchandise_orders (id VARCHAR(36) PRIMARY KEY, order_number VARCHAR(50) NOT NULL UNIQUE, customer_name VARCHAR NOT NULL, customer_phone VARCHAR NOT NULL, customer_email VARCHAR, product_id VARCHAR NOT NULL, product_name VARCHAR NOT NULL, variant_id VARCHAR, variant_name VARCHAR, size VARCHAR, color VARCHAR, quantity INTEGER NOT NULL DEFAULT 1, unit_price FLOAT NOT NULL, total_price FLOAT NOT NULL, currency VARCHAR(10) NOT NULL DEFAULT 'KES', fulfillment_type VARCHAR(20) NOT NULL DEFAULT 'pickup', delivery_address TEXT, notes TEXT, status VARCHAR(20) NOT NULL DEFAULT 'pending', payment_status VARCHAR(20) NOT NULL DEFAULT 'unpaid', payment_method VARCHAR(30) NOT NULL DEFAULT 'mpesa', payment_reference VARCHAR(100), admin_notes TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
                "CREATE INDEX IF NOT EXISTS ix_users_status ON users(status);",
                "CREATE INDEX IF NOT EXISTS ix_users_created_at ON users(created_at);",
                "CREATE INDEX IF NOT EXISTS ix_applications_status ON applications(status);",
                "CREATE INDEX IF NOT EXISTS ix_applications_submitted_at ON applications(submitted_at);",
                "CREATE INDEX IF NOT EXISTS ix_events_event_date ON events(event_date);",
                "CREATE INDEX IF NOT EXISTS ix_certificates_issued_at ON certificates(issued_at);",
                "CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);",
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);",
                "ALTER TABLE mpesa_transactions ADD COLUMN IF NOT EXISTS order_number VARCHAR(50);",
                "ALTER TABLE mpesa_transactions ADD COLUMN IF NOT EXISTS purpose VARCHAR(30) DEFAULT 'membership';",
                "CREATE TABLE IF NOT EXISTS stripe_transactions (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) REFERENCES users(id), order_number VARCHAR(50), session_id VARCHAR(200) NOT NULL UNIQUE, payment_intent_id VARCHAR(200), amount FLOAT NOT NULL, currency VARCHAR(10) NOT NULL DEFAULT 'USD', status VARCHAR(30) NOT NULL DEFAULT 'initiated', purpose VARCHAR(30) NOT NULL DEFAULT 'membership', customer_email VARCHAR, raw_event TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
                "CREATE INDEX IF NOT EXISTS ix_stripe_session_id ON stripe_transactions(session_id);",
                "CREATE INDEX IF NOT EXISTS ix_stripe_user_id ON stripe_transactions(user_id);",
                "CREATE INDEX IF NOT EXISTS ix_stripe_order_number ON stripe_transactions(order_number);",
            ]:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    if is_sqlite and "ADD COLUMN IF NOT EXISTS" in stmt:
                        try:
                            fallback_stmt = stmt.replace("ADD COLUMN IF NOT EXISTS", "ADD COLUMN")
                            await conn.execute(text(fallback_stmt))
                        except Exception:
                            pass
        print("Database schema verified/created successfully.")

        # Load maintenance mode state on startup
        try:
            from sqlalchemy import select

            from app.database import AsyncSessionLocal
            from app.models import SystemSettings
            from app.routers import admin as admin_router

            async with AsyncSessionLocal() as session:
                sett = await session.scalar(
                    select(SystemSettings).where(
                        SystemSettings.key == "maintenance_mode"
                    )
                )
                if sett and sett.value == "true":
                    admin_router.app_state.MAINTENANCE_MODE = True
                else:
                    admin_router.app_state.MAINTENANCE_MODE = False
        except Exception as e:
            print(f"Warning: Failed to load maintenance mode on startup: {e}")

        # Ensure default super_admin accounts exist on startup
        try:
            from sqlalchemy import select
            from app.auth import get_password_hash
            from app.database import AsyncSessionLocal
            from app.models import User

            # SECURITY: there is NO built-in default password. Bootstrap admin accounts are
            # only created when ADMIN_INITIAL_PASSWORD is set (12+ chars), and they are forced
            # to change that password at first login. Existing accounts are never modified
            # (in particular, nobody is silently promoted to super_admin).
            initial_pw = (os.environ.get("ADMIN_INITIAL_PASSWORD") or "").strip()
            if len(initial_pw) < 12:
                if initial_pw:
                    print("Warning: ADMIN_INITIAL_PASSWORD is shorter than 12 characters; skipping bootstrap admin creation.")
            else:
                default_admins = [
                    {
                        "id": "b314c169-d766-47f3-ad1d-107383eef6b4",
                        "email": "brianmuema928@gmail.com",
                        "full_name": "Brian Muema",
                        "role": "super_admin",
                    },
                    {
                        "id": "e494cd3e-9973-4ccf-a024-f54e8f372045",
                        "email": "rayazenlyx@gmail.com",
                        "full_name": "Raya Zenlyx",
                        "role": "super_admin",
                    },
                ]
                async with AsyncSessionLocal() as session:
                    for admin_data in default_admins:
                        admin_user = await session.scalar(
                            select(User).where(User.email == admin_data["email"])
                        )
                        if not admin_user:
                            session.add(
                                User(
                                    id=admin_data["id"],
                                    email=admin_data["email"],
                                    full_name=admin_data["full_name"],
                                    role=admin_data["role"],
                                    password_hash=get_password_hash(initial_pw),
                                    status="active",
                                    email_verified=True,
                                    must_change_password=True,
                                )
                            )
                            print(f"Bootstrap super_admin account created: {admin_data['email']}")
                    await session.commit()
        except Exception as e:
            print(f"Warning: Failed to ensure default admin account on startup: {e}")

    except Exception as e:
        print(f"Warning: Failed to create tables on startup: {e}")
    yield


app = FastAPI(title="Insight Circle API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
import os

_DEFAULT_ORIGINS = ",".join(
    [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://insightcirclepalace.com",
        "https://www.insightcirclepalace.com",
        "https://insightcirclepalace.org",
        "https://www.insightcirclepalace.org",
        "https://insight-circle-palace.vercel.app",
        "https://admin.insight-circle-palace.vercel.app",
        "https://insight-circle-admin.vercel.app",
    ]
)
origins_str = os.environ.get("CORS_ORIGINS") or _DEFAULT_ORIGINS
origins = sorted({origin.strip().rstrip("/") for origin in origins_str.split(",") if origin.strip()})

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
)


@app.middleware("http")
async def canonical_host_middleware(request: Request, call_next):
    # 1. Never redirect mutations or non-safe HTTP methods (POST, PUT, DELETE, PATCH, OPTIONS)
    # Redirecting POST/PUT/DELETE drops the request body and fails browser CORS preflight with credentials
    if request.method not in ("GET", "HEAD"):
        return await call_next(request)

    # 2. Never redirect API, authentication, admin, static, or health check routes
    path = request.url.path
    api_prefixes = (
        "/auth",
        "/api",
        "/admin",
        "/admin_app",
        "/applications",
        "/assignments",
        "/programs",
        "/events",
        "/analytics",
        "/certificates",
        "/quizzes",
        "/seasons",
        "/feedback",
        "/static",
        "/assets",
        "/health",
        "/robots.txt",
        "/sitemap.xml",
        "/favicon.ico",
    )
    if path.startswith(api_prefixes):
        return await call_next(request)

    host = request.headers.get("host", "").lower().split(":")[0]

    # In production on Vercel, domain redirects are handled at the CDN/DNS edge.
    # Avoid redirecting www.insightcirclepalace.com back to apex if Vercel redirects apex to www.
    if os.environ.get("VERCEL") == "1" and host == "www.insightcirclepalace.com":
        return await call_next(request)

    if host in ("www.insightcirclepalace.com", "insightcirclepalace.org", "www.insightcirclepalace.org"):
        query = f"?{request.url.query}" if request.url.query else ""
        return RedirectResponse(
            url=f"https://insightcirclepalace.com{path}{query}",
            status_code=301,
        )
    return await call_next(request)


# Content-Security-Policy.
# ENFORCED: the directives that block clickjacking, <base> hijacking and plugin content
# without affecting any page. REPORT-ONLY: the full policy (script/style/img sources), so you
# can watch the browser console for violations and then promote it to enforced.
_CSP_ENFORCED = "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
_CSP_REPORT_ONLY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com "
    "https://cdn.jsdelivr.net https://cdn.quilljs.com https://www.googletagmanager.com "
    "https://accounts.google.com https://apis.google.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com "
    "https://cdn.jsdelivr.net https://cdn.quilljs.com https://accounts.google.com; "
    "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
    "img-src 'self' data: blob: https:; "
    "media-src 'self' blob: https:; "
    "frame-src 'self' https://accounts.google.com https://drive.google.com https://docs.google.com "
    "https://www.youtube.com https://www.youtube-nocookie.com https://player.vimeo.com "
    "https://meet.google.com; "
    "connect-src 'self' https://*.google-analytics.com https://*.analytics.google.com "
    "https://www.googletagmanager.com https://accounts.google.com; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)

_UNSAFE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


@app.middleware("http")
async def csrf_origin_check(request: Request, call_next):
    """Reject cross-site state-changing requests that carry the login cookie.

    Browsers always send an Origin header on cross-site POST/PUT/PATCH/DELETE. If it is present
    and is neither this site nor an allowed origin, the request is refused. Server-to-server
    webhooks (Stripe, M-Pesa) carry no session cookie and are not affected.
    """
    if request.method in _UNSAFE_METHODS and request.cookies.get("insight_session"):
        origin = (request.headers.get("origin") or "").rstrip("/")
        if origin and origin != "null":
            host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
            same_site = origin.split("://", 1)[-1] == host
            if not same_site and origin not in origins:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-site request blocked."},
                )
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )
    response.headers["Content-Security-Policy"] = _CSP_ENFORCED
    response.headers["Content-Security-Policy-Report-Only"] = _CSP_REPORT_ONLY
    # Don't let browsers/CDNs cache authenticated API responses
    # Every dynamic response (API, events, programs, settings...) must always be fresh so that
    # admin-portal edits show on the public site immediately. Only real static files are exempt.
    _path = request.url.path
    if not _path.startswith(("/static", "/assets", "/admin_app/", "/admin/js", "/admin/css")) \
            and "cache-control" not in response.headers:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import sys
    import traceback

    print(
        f"Unhandled exception on {request.method} {request.url}: {exc}", file=sys.stderr
    )
    traceback.print_exc()
    import os

    content = {"detail": f"Internal server error: {str(exc)}" if os.environ.get("APP_ENV") == "development" else "Internal server error"}
    return JSONResponse(
        status_code=500,
        content=content,
    )


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        import os

        content = {"status": "error", "db": "disconnected"}
        if os.environ.get("APP_ENV") == "development":
            content["error"] = str(e)
        return JSONResponse(status_code=500, content=content)


# Include Routers
app.include_router(auth.router)
app.include_router(applications.router)
app.include_router(programs.router)
app.include_router(quizzes.router)
app.include_router(certificates.router)
app.include_router(events.router)
app.include_router(recordings.router)
app.include_router(recordings.admin_recordings_router)
app.include_router(monday_sessions.router)
app.include_router(monday_sessions.admin_monday_router)
app.include_router(memberships.router)
app.include_router(memberships.admin_membership_router)
app.include_router(admin.router)
app.include_router(admin.router, prefix="/api")
app.include_router(analytics.router)
app.include_router(seasons.router)
app.include_router(certification.router)
app.include_router(feedback.router)
app.include_router(assignments.router)
app.include_router(payments.router)
app.include_router(merchandise.router)
app.include_router(merchandise.admin_merchandise_router)
app.include_router(mpesa.router)
app.include_router(mpesa.admin_mpesa_router)
app.include_router(stripe.router)


# Mount static files

from typing import Optional

from pydantic import BaseModel


class InsightersMondayConfig(BaseModel):
    date: Optional[str] = ""
    banner_short_description: Optional[str] = ""
    full_session_description: Optional[str] = ""
    poster_url: Optional[str] = ""
    registration_link: Optional[str] = ""
    is_active: Optional[bool] = False
    meeting_link: Optional[str] = ""
    recording_link: Optional[str] = ""


@app.get("/api/public/settings")
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    from sqlalchemy.future import select

    from app.models import SystemSettings

    public_keys = [
        "org-name",
        "support-email",
        "support-phone",
        "whatsapp-number",
        "hero-text",
        "stats-members",
        "stats-countries",
        "stats-rating",
        "instagram-url",
        "linkedin-url",
        "facebook-url",
        "chat-welcome-message",
        "chat-tagline",
        "announcement-text",
        "announcement-link",
        "announcement-active",
    ]

    result = await db.scalars(
        select(SystemSettings).where(SystemSettings.key.in_(public_keys))
    )
    settings = result.all()

    settings_dict = {
        "org-name": "Insight Circle Palace",
        "support-email": "Insightcirclepalace@gmail.com",
        "support-phone": "+254 768 371 417",
        "whatsapp-number": "254768371417",
        "hero-text": 'Professional Development & <br class="hidden lg:block">\n<span class="text-gold">Leadership Platform</span>',
        "stats-members": "5,000+ Members",
        "stats-countries": "15+ Countries",
        "stats-rating": "4.9/5 Rating",
        "instagram-url": "https://www.instagram.com/insight_circlepalace?igsh=eG50enFranY3eGdv&igsi=eG50enFranY3eGdv",
        "linkedin-url": "https://www.linkedin.com/company/insight-circle-palace",
        "facebook-url": "https://www.facebook.com/insightcirclepalace",
        "chat-welcome-message": "Welcome to Insight Circle Palace!\nWhere Knowledge Meets Opportunity.\n\nWe are a premier platform empowering the next generation through practical skills, leadership, technology, entrepreneurship, and career opportunities.\n\nHow can we help you today?",
        "chat-tagline": "Where Knowledge Meets Opportunity.",
        "announcement-text": "",
        "announcement-link": "",
        "announcement-active": "false",
    }

    for s in settings:
        if s.value:
            settings_dict[s.key] = s.value

    return JSONResponse(
        content=settings_dict,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )



def is_session_date_passed(date_str: str) -> bool:
    if not date_str or not isinstance(date_str, str):
        return False
    import re
    from datetime import datetime, timezone, timedelta
    s = date_str.strip()
    eat_tz = timezone(timedelta(hours=3))
    now_eat = datetime.now(eat_tz)
    
    # Try DD/MM/YYYY
    m = re.search(r'(?:[A-Za-z]+[,\s]+)?(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', s)
    if m:
        try:
            day = int(m.group(1))
            month = int(m.group(2))
            year = int(m.group(3))
            session_end = datetime(year, month, day, 21, 30, tzinfo=eat_tz)
            return now_eat > session_end
        except Exception:
            pass
            
    # Try YYYY-MM-DD
    m2 = re.search(r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})', s)
    if m2:
        try:
            year = int(m2.group(1))
            month = int(m2.group(2))
            day = int(m2.group(3))
            session_end = datetime(year, month, day, 21, 30, tzinfo=eat_tz)
            return now_eat > session_end
        except Exception:
            pass
    return False

@app.get("/api/public/insighters_monday")
async def get_insighters_monday(db: AsyncSession = Depends(get_db)):
    import json

    from sqlalchemy.future import select

    from app.models import SystemSettings

    result = await db.scalars(
        select(SystemSettings).where(SystemSettings.key == "insighters_monday")
    )
    setting = result.first()

    if setting and setting.value:
        try:
            return JSONResponse(
                content=json.loads(setting.value),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )
        except json.JSONDecodeError:
            pass

    return JSONResponse(
        content={
            "date": "",
            "banner_short_description": "",
            "full_session_description": "",
            "poster_url": "",
            "registration_link": "",
            "is_active": False,
        },
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


from app.schemas import EnquiryCreate


@app.post("/api/public/enquiries", status_code=201)
@limiter.limit("5/minute;30/hour")
async def create_public_enquiry(
    request: Request, enquiry_data: EnquiryCreate, db: AsyncSession = Depends(get_db)
):
    from fastapi import HTTPException

    from app.models import ContactEnquiry, utcnow

    clean_msg = (enquiry_data.message or "").strip()
    if not clean_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if len(clean_msg) > 5000:
        raise HTTPException(status_code=400, detail="Message is too long")

    clean_name = (enquiry_data.name or "").strip()[:100] or None
    clean_email = (enquiry_data.email or "").strip()[:150] or None
    clean_phone = (enquiry_data.phone or "").strip()[:50] or None
    clean_source = (enquiry_data.source or "website_chat").strip()[:50]

    new_enquiry = ContactEnquiry(
        name=clean_name,
        email=clean_email,
        phone=clean_phone,
        message=clean_msg,
        status="New",
        source=clean_source,
        session_id=enquiry_data.session_id,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(new_enquiry)
    await db.commit()
    await db.refresh(new_enquiry)
    return {
        "status": "ok",
        "id": new_enquiry.id,
        "message": "Enquiry submitted successfully",
    }


class NewsletterSubscribe(BaseModel):
    email: str


@app.post("/api/public/subscribe", status_code=201)
@limiter.limit("5/minute;20/hour")
async def subscribe_newsletter(
    request: Request, sub_data: NewsletterSubscribe, db: AsyncSession = Depends(get_db)
):
    from fastapi import HTTPException

    from app.models import ContactEnquiry, utcnow

    clean_email = (sub_data.email or "").strip().lower()
    import re

    if (
        not clean_email
        or len(clean_email) > 150
        or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]{2,}", clean_email)
    ):
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")

    new_sub = ContactEnquiry(
        name="Newsletter Subscriber",
        email=clean_email,
        message="Newsletter subscription request",
        status="New",
        source="newsletter_footer",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(new_sub)
    await db.commit()
    return {"status": "ok", "message": "Thank you for subscribing! We will keep you updated."}


@app.get("/api/public/latest-update")
async def get_latest_update(db: AsyncSession = Depends(get_db)):
    import json
    from datetime import datetime, timezone

    from sqlalchemy import desc, func
    from sqlalchemy.future import select

    from app.models import Certificate, Event, Program, SystemSettings

    def _normalize_dt(dt):
        if not dt:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    candidates = []

    # 1. Programs (ordered by coalesce(updated_at, created_at) desc)
    try:
        prog_stmt = (
            select(Program)
            .where(Program.is_active == True)
            .order_by(desc(func.coalesce(Program.updated_at, Program.created_at)))
            .limit(5)
        )
        prog_res = await db.execute(prog_stmt)
        for p in prog_res.scalars().all():
            p_dt = _normalize_dt(getattr(p, "updated_at", None) or p.created_at)
            c_dt = _normalize_dt(p.created_at)
            is_new = abs((p_dt - c_dt).total_seconds()) < 120
            clean_desc = (
                (p.description or "")
                .replace("<p>", "")
                .replace("</p>", " ")
                .replace("<br>", " ")
                .strip()
            )
            msg_text = (
                (clean_desc[:90] + "...")
                if len(clean_desc) > 90
                else (clean_desc or "Explore our newest track and curriculum.")
            )

            candidates.append(
                {
                    "id": f"program_{p.id}_{int(p_dt.timestamp())}",
                    "type": "program",
                    "action": "created" if is_new else "updated",
                    "badge": "NEW PROGRAM" if is_new else "PROGRAM UPDATE",
                    "title": (
                        f"New Program: {p.title}"
                        if is_new
                        else f"Updated Program: {p.title}"
                    ),
                    "message": msg_text,
                    "link": f"/static/explore.html#{p.slug}",
                    "cta_text": "Explore Program Track →",
                    "timestamp": p_dt.isoformat(),
                    "_dt": p_dt,
                }
            )
    except Exception as e:
        pass

    # 2. Insighters Monday
    try:
        sett_res = await db.execute(
            select(SystemSettings).where(SystemSettings.key == "insighters_monday")
        )
        im_setting = sett_res.scalars().first()
        if im_setting and im_setting.value:
            val = {}
            try:
                val = json.loads(im_setting.value)
            except Exception:
                pass
            im_is_active = bool(val.get("is_active", False))
            im_date_str = str(val.get("date", ""))
            im_passed = is_session_date_passed(im_date_str)
            im_dt = _normalize_dt(
                im_setting.updated_at or getattr(im_setting, "created_at", None)
            )
            desc_text = (
                val.get("banner_short_description")
                or val.get("date")
                or "New edition of Insighters Monday is live!"
            )
            reg_link = (
                val.get("registration_link") or "/static/index.html#insighters-monday"
            )

            if im_is_active and not im_passed:
                candidates.append(
                    {
                        "id": f"monday_{im_setting.id}_{int(im_dt.timestamp())}",
                        "type": "insighters_monday",
                        "action": "upcoming_session",
                        "badge": "UPCOMING SESSION",
                        "title": "Insighters Monday",
                        "message": f"Register for the upcoming session: {desc_text}",
                        "link": reg_link,
                        "cta_text": "Register for upcoming session →",
                        "timestamp": im_dt.isoformat(),
                        "_dt": im_dt,
                        "is_active": im_is_active,
                    }
                )
    except Exception as e:
        pass

    # 3. Events
    try:
        evt_stmt = (
            select(Event)
            .order_by(desc(func.coalesce(Event.updated_at, Event.created_at)))
            .limit(5)
        )
        evt_res = await db.execute(evt_stmt)
        for e in evt_res.scalars().all():
            e_dt = _normalize_dt(getattr(e, "updated_at", None) or e.created_at)
            c_dt = _normalize_dt(e.created_at)
            is_new = abs((e_dt - c_dt).total_seconds()) < 120
            candidates.append(
                {
                    "id": f"event_{e.id}_{int(e_dt.timestamp())}",
                    "type": "event",
                    "action": "created" if is_new else "updated",
                    "badge": "UPCOMING EVENT",
                    "title": (
                        f"New Event: {e.title}"
                        if is_new
                        else f"Updated Event: {e.title}"
                    ),
                    "message": (
                        e.subtitle
                        or e.description
                        or "Register now for our upcoming session."
                    )[:95],
                    "link": f"/static/events.html#event-{e.id}",
                    "cta_text": "Register for Event →",
                    "timestamp": e_dt.isoformat(),
                    "_dt": e_dt,
                }
            )
    except Exception as e:
        pass

    if not candidates:
        return JSONResponse(
            content={"update": None},
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    candidates.sort(key=lambda x: x["_dt"], reverse=True)
    top_update = candidates[0].copy()
    top_update.pop("_dt", None)
    return JSONResponse(
        content={"update": top_update},
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.post("/api/admin/insighters_monday")
async def update_insighters_monday(
    config: InsightersMondayConfig,
    admin: User = Depends(require_roles(["admin", "super_admin", "editor", "event_manager", "program_manager"])),
    db: AsyncSession = Depends(get_db),
):
    import json

    from sqlalchemy.future import select

    from app.models import SystemSettings, utcnow

    result = await db.scalars(
        select(SystemSettings).where(SystemSettings.key == "insighters_monday")
    )
    setting = result.first()

    if setting:
        setting.value = json.dumps(config.model_dump())
        setting.updated_at = utcnow()
    else:
        setting = SystemSettings(
            key="insighters_monday",
            value=json.dumps(config.model_dump()),
            updated_at=utcnow(),
        )
        db.add(setting)

    await db.commit()
    return {"status": "success"}


@app.post("/api/admin/upload-image")
async def upload_admin_image(
    file: UploadFile = File(...),
    admin: User = Depends(require_roles(["admin", "super_admin", "editor", "event_manager", "program_manager", "certificate_manager", "moderator"])),
    db: AsyncSession = Depends(get_db),
):
    import base64
    import io
    import os
    import uuid

    from PIL import Image, ImageOps

    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_extensions:
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid file type. Please upload an image (.jpg, .png, .webp)."},
        )

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"detail": "File size exceeds 15MB limit."})

    try:
        img = Image.open(io.BytesIO(content))
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        max_dim = 1400
        if max(img.width, img.height) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="WEBP", quality=85, method=6)
        compressed_bytes = buffer.getvalue()
    except Exception:
        # Not a decodable image: refuse it instead of storing arbitrary bytes under a .webp name.
        return JSONResponse(
            status_code=400,
            content={"detail": "The uploaded file is not a valid image."},
        )

    filename = f"{uuid.uuid4().hex}.webp"
    uploads_dir = os.path.join("static", "uploads")
    try:
        os.makedirs(uploads_dir, exist_ok=True)
        filepath = os.path.join(uploads_dir, filename)
        with open(filepath, "wb") as f:
            f.write(compressed_bytes)
        return {"url": f"/static/uploads/{filename}"}
    except Exception:
        b64 = base64.b64encode(compressed_bytes).decode("utf-8")
        return {"url": f"data:image/webp;base64,{b64}"}


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")
app.mount("/admin_app/js", StaticFiles(directory="admin_app/js"), name="admin_app_js")
if os.path.exists("admin_app/css"):
    app.mount("/admin_app/css", StaticFiles(directory="admin_app/css"), name="admin_app_css")
app.mount("/admin/js", StaticFiles(directory="admin_app/js"), name="admin_js")
if os.path.exists("admin_app/css"):
    app.mount("/admin/css", StaticFiles(directory="admin_app/css"), name="admin_css")


ADMIN_PORTAL_ROLES = [
    "admin",
    "super_admin",
    "program_manager",
    "event_manager",
    "certificate_manager",
    "analyst",
    "editor",
    "moderator",
]

async def check_admin_page_access(request: Request, db: AsyncSession):
    user = await get_optional_user(request, db)
    if not user:
        return "unauthenticated"
    if user.role not in ADMIN_PORTAL_ROLES:
        return "unauthorized"
    return user


@app.get("/")
async def root():
    return FileResponse("static/index.html", media_type="text/html")


@app.get("/admin_portal", include_in_schema=False)
@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
@app.get("/admin_app", include_in_schema=False)
@app.get("/admin_app/", include_in_schema=False)
async def admin_portal_entry(request: Request, db: AsyncSession = Depends(get_db)):
    access = await check_admin_page_access(request, db)
    if access == "unauthenticated":
        return RedirectResponse(url="/admin/login", status_code=302)
    if access == "unauthorized":
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@app.get("/admin/login", include_in_schema=False)
@app.get("/admin_app/login.html", include_in_schema=False)
async def admin_login_page():
    return FileResponse("admin_app/login.html", media_type="text/html", headers={"Cache-Control": "no-cache, must-revalidate"})


@app.get("/admin/dashboard", include_in_schema=False)
@app.get("/admin/dashboard/", include_in_schema=False)
@app.get("/admin_app/dashboard", include_in_schema=False)
@app.get("/admin_app/dashboard.html", include_in_schema=False)
async def admin_dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    access = await check_admin_page_access(request, db)
    if access == "unauthenticated":
        return RedirectResponse(url="/admin/login", status_code=302)
    if access == "unauthorized":
        return RedirectResponse(url="/dashboard", status_code=302)
    return FileResponse("admin_app/dashboard.html", media_type="text/html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    base_url = os.getenv("BASE_URL", os.getenv("SITE_URL", "")).rstrip("/")
    if os.path.exists("static/robots.txt"):
        with open("static/robots.txt", "r", encoding="utf-8") as f:
            content = f.read()
        if base_url:
            content = content.replace("https://insightcirclepalace.com", base_url).replace("https://insightcirclepalace.org", base_url)
        return Response(content=content, media_type="text/plain")
    return FileResponse("robots.txt", media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    base_url = os.getenv("BASE_URL", os.getenv("SITE_URL", "")).rstrip("/")
    if os.path.exists("static/sitemap.xml"):
        with open("static/sitemap.xml", "r", encoding="utf-8") as f:
            content = f.read()
        if base_url:
            content = content.replace("https://insightcirclepalace.com", base_url).replace("https://insightcirclepalace.org", base_url)
        return Response(content=content, media_type="application/xml")
    return FileResponse("sitemap.xml", media_type="application/xml")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse("static/assets/favicon-32x32.png", media_type="image/png")


@app.get("/google{code}.html", include_in_schema=False)
async def google_site_verification(code: str):
    for candidate in [f"static/google{code}.html", f"google{code}.html"]:
        if os.path.exists(candidate):
            return FileResponse(candidate, media_type="text/html")
    return JSONResponse(status_code=404, content={"detail": "Verification file not found"})


# --- Clean Public & Application Routes ---
PAGE_ROUTES = [
    "explore", "join", "login", "register", "onboard",
    "dashboard", "profile", "my-events", "my-programs",
    "certificates", "verify", "reset-password", "feedback",
    "privacy-policy", "terms", "terms-and-conditions", "maintenance", "learn", "tech-ai",
    "leadership", "finance", "entrepreneurship", "research",
    "wellness", "relationships", "healing", "ai-strategy-executive",
    "assignments", "recordings", "monday-registration", "merchandise"
]

def make_page_handler(page_name: str):
    async def handler():
        filepath = os.path.join("static", f"{page_name}.html")
        if os.path.exists(filepath):
            return FileResponse(filepath, media_type="text/html")
        return FileResponse("static/404.html", status_code=404)
    return handler

for p in PAGE_ROUTES:
    app.add_api_route(f"/{p}", make_page_handler(p), methods=["GET"], include_in_schema=False)
    app.add_api_route(f"/{p}.html", make_page_handler(p), methods=["GET"], include_in_schema=False)

# Dedicated handler for events.html (since /events is in events.router)
@app.get("/events.html", include_in_schema=False)
async def events_html_page():
    return FileResponse("static/events.html", media_type="text/html")


@app.get("/monday-session", include_in_schema=False)
@app.get("/monday-sessions", include_in_schema=False)
@app.get("/monday-sessions.html", include_in_schema=False)
async def monday_session_redirect():
    return FileResponse("static/monday-registration.html", media_type="text/html")




@app.get("/admin/{subpath:path}", include_in_schema=False)
async def admin_nested_route_guard(subpath: str, request: Request, db: AsyncSession = Depends(get_db)):
    access = await check_admin_page_access(request, db)
    if access == "unauthenticated":
        return RedirectResponse(url="/admin/login", status_code=302)
    if access == "unauthorized":
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header and os.path.exists("static/404.html"):
            return FileResponse("static/404.html", status_code=404)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
