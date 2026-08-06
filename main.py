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
from app.routers import auth, applications, programs, certificates

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "db": "disconnected", "error": str(e)}
        )

# Include Routers
app.include_router(auth.router)
app.include_router(applications.router)
app.include_router(programs.router)
app.include_router(certificates.router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

