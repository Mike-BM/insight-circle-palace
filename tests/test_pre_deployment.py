import asyncio
import os
import sys
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal, Base, engine
from app.models import ContactEnquiry, AnalyticsEvent
from main import app


def test_clean_url_routing():
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Root route
            res_root = await ac.get("/")
            assert res_root.status_code == 200
            assert "text/html" in res_root.headers.get("content-type", "")
            assert "Insight Circle" in res_root.text

            # 2. Clean application routes
            for path in ["/explore", "/join", "/tech-ai", "/leadership", "/finance"]:
                res = await ac.get(path)
                assert res.status_code == 200, f"Failed for path {path}: {res.status_code}"
                assert "text/html" in res.headers.get("content-type", "")

            # 3. Dual routing for events (HTML vs JSON)
            html_res = await ac.get("/events", headers={"Accept": "text/html,application/xhtml+xml"})
            assert html_res.status_code == 200
            assert "text/html" in html_res.headers.get("content-type", "")
            assert "Events & Executive Masterclasses" in html_res.text

            json_res = await ac.get("/events/", headers={"Accept": "application/json"})
            assert json_res.status_code == 200
            assert isinstance(json_res.json(), list)

            # 4. Robots.txt
            robots_res = await ac.get("/robots.txt")
            assert robots_res.status_code == 200
            assert "https://insightcirclepalace.com/sitemap.xml" in robots_res.text
            assert "Disallow: /admin" in robots_res.text

            # 5. Sitemap.xml
            sitemap_res = await ac.get("/sitemap.xml")
            assert sitemap_res.status_code == 200
            assert "https://insightcirclepalace.com/" in sitemap_res.text
            assert "https://insightcirclepalace.com/explore" in sitemap_res.text

            # 6. Google Verification Route (404 for nonexistent code)
            google_res = await ac.get("/google12345test.html")
            assert google_res.status_code == 404

    asyncio.run(_run())


def test_newsletter_subscription():
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            test_email = f"newsletter_{uuid.uuid4().hex[:6]}@example.com"

            # 1. Successful subscription
            res = await ac.post("/api/public/subscribe", json={"email": test_email, "name": "Newsletter Fan"})
            assert res.status_code in [200, 201], f"Subscription failed: {res.text}"
            data = res.json()
            assert data["status"] in ["ok", "success"]
            assert "Thank you" in data["message"]

            # Verify in DB
            async with AsyncSessionLocal() as session:
                enq_res = await session.execute(
                    select(ContactEnquiry).where(ContactEnquiry.email == test_email)
                )
                enquiry = enq_res.scalars().first()
                assert enquiry is not None
                assert enquiry.source == "newsletter_footer"

            # 2. Invalid email format
            invalid_res = await ac.post("/api/public/subscribe", json={"email": "not-an-email"})
            assert invalid_res.status_code in [400, 422]

    asyncio.run(_run())


def test_analytics_tracking():
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Valid tracking event
            res = await ac.post("/analytics/track", json={
                "event_type": "pageview",
                "path": "/explore",
                "metadata": {"referrer": "direct"}
            })
            assert res.status_code == 200
            assert res.json() == {"status": "ok"}

            # 2. Invalid tracking event (missing required event_type)
            bad_res = await ac.post("/analytics/track", json={
                "path": "/explore"
            })
            assert bad_res.status_code == 422

    asyncio.run(_run())
