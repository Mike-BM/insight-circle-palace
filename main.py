import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.models import ApplicationSubmit, ApplicationRecord
from app.sorting import assign_path
from app.timer import compute_unlock_at
from app.db import applications
from app.scheduler import sweep_pending_applications

app = FastAPI(title="Insight Circle API")

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
    applications[record.id] = record
    return {"status": "success", "application_id": record.id}

class LoginRequest(BaseModel):
    application_id: str

@app.post("/applications/login")
async def login_application(req: LoginRequest):
    record = applications.get(req.application_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
        
    now = datetime.utcnow()
    # Dynamic self-correction if sweeper hasn't run yet
    if record.status == "pending" and now >= record.unlock_at:
        record.status = "approved"
        
    if record.status == "approved":
        return {"status": "approved", "path": record.path}
    else:
        seconds_remaining = int((record.unlock_at - now).total_seconds())
        return {"status": "pending", "seconds_remaining": max(0, seconds_remaining)}
