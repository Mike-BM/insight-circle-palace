import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from urllib.parse import quote

from app.models import ApplicationSubmit, ApplicationRecord
from app.sorting import assign_path
from app.timer import compute_unlock_at
from app.db import applications
from app.scheduler import sweep_pending_applications

app = FastAPI(title="Insight Circle API")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.lower()
        
        protected_pages = {
            "/static/entrepreneurship.html",
            "/static/finance.html",
            "/static/healing.html",
            "/static/leadership.html",
            "/static/relationships.html",
            "/static/research.html",
            "/static/tech-ai.html",
            "/static/wellness.html"
        }
        
        auth_cookie = request.cookies.get("insight_session")
        is_authenticated = bool(auth_cookie)
        
        if not is_authenticated and path in protected_pages:
            msg = quote("Please log in to access this feature")
            redirect_url = f"/static/index.html?msg={msg}"
            return RedirectResponse(url=redirect_url)
            
        if is_authenticated and path in {"/static/login.html", "/static/join.html"}:
            return RedirectResponse(url="/static/index.html")
            
        response = await call_next(request)
        return response

app.add_middleware(AuthMiddleware)

@app.on_event("startup")
async def startup_event():
    # Start the background scheduler to auto-approve applications
    asyncio.create_task(sweep_pending_applications())

# Mount the static directory to serve HTML, CSS, JS, and assets
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    # Redirect root to the index.html served from static directory
    return RedirectResponse(url="/static/index.html")

# Placeholder API endpoints
@app.get("/api/stats")
async def get_stats():
    return {
        "members": 15000,
        "countries": 45,
        "workshops": 320,
        "projects": 1200,
        "mentors": 150
    }

@app.get("/api/events")
async def get_events():
    return [
        {
            "id": 1,
            "title": "Global AI Innovation Summit",
            "date": "2026-08-15",
            "format": "Hybrid",
            "location": "London, UK / Virtual",
            "type": "Conference"
        },
        {
            "id": 2,
            "title": "Future Founders Hackathon",
            "date": "2026-09-10",
            "format": "In-Person",
            "location": "New York, USA",
            "type": "Hackathon"
        },
        {
            "id": 3,
            "title": "Healthcare Tech Seminar",
            "date": "2026-10-05",
            "format": "Virtual",
            "location": "Online",
            "type": "Webinar"
        }
    ]

@app.post("/applications/submit")
async def submit_application(submit: ApplicationSubmit):
    path = assign_path(submit.q5_focus)
    unlock_at = compute_unlock_at()
    record = ApplicationRecord.create(
        answers=submit,
        path=path,
        unlock_at=unlock_at
    )
    applications[record.username] = record
    return {"status": "success", "username": record.username}

class LoginRequest(BaseModel):
    username: str

@app.post("/applications/login")
async def login_application(req: LoginRequest, response: Response):
    # Local dev mode: allow any username to log in instantly
    response.set_cookie(key="insight_session", value=req.username, httponly=True)
    return {"status": "approved"}

@app.post("/applications/logout")
async def logout_application(response: Response):
    response.delete_cookie(key="insight_session")
    return {"status": "success"}
