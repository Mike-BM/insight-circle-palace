from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Insight Circle API")

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
