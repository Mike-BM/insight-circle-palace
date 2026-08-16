import asyncio
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
import uvicorn
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from contextlib import asynccontextmanager
from app.database import get_db, engine, Base
from app.routers import auth, applications, programs, certificates, events, recordings, oauth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created on startup
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database schema verified/created successfully.")
    except Exception as e:
        print(f"Warning: Failed to create tables on startup: {e}")
    yield

app = FastAPI(title="Insight Circle API", lifespan=lifespan)

# Add CORS middleware for production resilience
import os
origins_str = os.environ.get("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000")
origins = [origin.strip() for origin in origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    import sys
    print(f"Unhandled exception on {request.method} {request.url}: {exc}", file=sys.stderr)
    traceback.print_exc()
    import os
    content = {"detail": "Internal server error"}
    if os.environ.get("APP_ENV") == "development":
        content["error"] = str(exc)
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
        return JSONResponse(
            status_code=500,
            content=content
        )

# Include Routers
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(applications.router)
app.include_router(programs.router)
app.include_router(certificates.router)
app.include_router(events.router)
app.include_router(recordings.router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

