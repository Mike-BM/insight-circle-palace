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

from app.auth import get_optional_user
from app.database import Base, engine, get_db
from app.routers import (admin, analytics, applications, assignments, auth, certificates, payments,
                         quizzes,
                         certification, events, feedback, memberships, monday_sessions, programs, recordings,
                         seasons, merchandise)


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
                "CREATE TABLE IF NOT EXISTS merchandise_orders (id VARCHAR(36) PRIMARY KEY, order_number VARCHAR(50) NOT NULL UNIQUE, customer_name VARCHAR NOT NULL, customer_phone VARCHAR NOT NULL, customer_email VARCHAR, product_id VARCHAR NOT NULL, product_name VARCHAR NOT NULL, variant_id VARCHAR, variant_name VARCHAR, size VARCHAR, color VARCHAR, quantity INTEGER NOT NULL DEFAULT 1, unit_price FLOAT NOT NULL, total_price FLOAT NOT NULL, currency VARCHAR(10) NOT NULL DEFAULT 'KES', fulfillment_type VARCHAR(20) NOT NULL DEFAULT 'pickup', delivery_address TEXT, notes TEXT, status VARCHAR(20) NOT NULL DEFAULT 'pending', payment_status VARCHAR(20) NOT NULL DEFAULT 'unpaid', payment_method VARCHAR(30) NOT NULL DEFAULT 'mpesa', payment_reference VARCHAR(100), admin_notes TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
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

    except Exception as e:
        print(f"Warning: Failed to create tables on startup: {e}")
    yield


app = FastAPI(title="Insight Circle API", lifespan=lifespan)
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware for production resilience
import os

origins_str = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000,https://admin.insight-circle-palace.vercel.app,https://insight-circle-admin.vercel.app,https://insight-circle-palace.vercel.app,https://insightcirclepalace.org,https://www.insightcirclepalace.org,https://insightcircle.org,https://www.insightcircle.org,https://insightcirclepalace.com,https://www.insightcirclepalace.com",
)
origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins
    + [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://admin.insight-circle-palace.vercel.app",
        "https://insight-circle-admin.vercel.app",
        "https://insight-circle-palace.vercel.app",
        "https://insightcirclepalace.org",
        "https://www.insightcirclepalace.org",
        "https://insightcircle.org",
        "https://www.insightcircle.org",
        "https://insightcirclepalace.com",
        "https://www.insightcirclepalace.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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
async def create_public_enquiry(
    enquiry_data: EnquiryCreate, db: AsyncSession = Depends(get_db)
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
async def subscribe_newsletter(
    sub_data: NewsletterSubscribe, db: AsyncSession = Depends(get_db)
):
    from fastapi import HTTPException

    from app.models import ContactEnquiry, utcnow

    clean_email = (sub_data.email or "").strip().lower()
    if not clean_email or "@" not in clean_email or len(clean_email) > 150:
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
    config: InsightersMondayConfig, request: Request, db: AsyncSession = Depends(get_db)
):
    import json

    from sqlalchemy.future import select

    from app.auth import get_optional_user
    from app.models import SystemSettings, utcnow

    # Verify admin
    admin = await get_optional_user(request, db)
    valid_admin_roles = [
        "admin",
        "super_admin",
        "editor",
        "event_manager",
        "program_manager",
    ]
    if not admin or admin.role not in valid_admin_roles:
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Unauthorized: Admin session expired or insufficient permissions. Please log in again."
            },
        )

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
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    import base64
    import io
    import os
    import uuid

    from PIL import Image, ImageOps

    from app.auth import get_optional_user

    admin = await get_optional_user(request, db)
    valid_admin_roles = [
        "admin",
        "super_admin",
        "editor",
        "event_manager",
        "program_manager",
        "certificate_manager",
        "moderator",
    ]
    if not admin or admin.role not in valid_admin_roles:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

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
        compressed_bytes = content

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
app.mount("/admin_app", StaticFiles(directory="admin_app", html=True), name="admin_app")


@app.get("/")
async def root():
    return FileResponse("static/index.html", media_type="text/html")


@app.get("/admin_portal")
async def admin_portal():
    return RedirectResponse(url="/admin_app/login.html")


@app.get("/admin")
@app.get("/admin/")
@app.get("/admin/login")
async def admin_fallback():
    return RedirectResponse(url="/admin_app/login.html")


@app.get("/admin/dashboard", include_in_schema=False)
async def admin_dashboard_page():
    return FileResponse("admin_app/dashboard.html", media_type="text/html")


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
async def monday_session_redirect():
    return FileResponse("static/monday-registration.html", media_type="text/html")




@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header and os.path.exists("static/404.html"):
            return FileResponse("static/404.html", status_code=404)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
