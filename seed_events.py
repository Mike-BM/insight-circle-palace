import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.database import AsyncSessionLocal, engine, Base
from app.models import Event
from datetime import datetime, timezone

async def seed_events():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        # Clear existing events to avoid duplicates during seeding
        await session.execute(delete(Event))
        
        events = [
            Event(
                title="INSIGHTIER SPOTLIGHT: Community Feature",
                description="Celebrating an Insightier's journey — growth, wins, and lessons from within our own circle.",
                event_date=datetime(2026, 8, 10, 17, 0, tzinfo=timezone.utc), # 8 PM EAT is 5 PM UTC
                meeting_link="https://zoom.us/j/dummy1"
            ),
            Event(
                title="GUEST SPEAKER: John Muthui",
                description="Career Without Borders: Thriving in the Online Work Economy.",
                event_date=datetime(2026, 8, 17, 17, 0, tzinfo=timezone.utc),
                meeting_link="https://zoom.us/j/dummy2"
            ),
            Event(
                title="GUEST SPEAKER: Mercy Makau",
                description="Topic: Artificial Intelligence — details to be confirmed.",
                event_date=datetime(2026, 8, 24, 17, 0, tzinfo=timezone.utc),
                meeting_link="https://zoom.us/j/dummy3"
            ),
            Event(
                title="GUEST MENTOR: Edwin Mwangi",
                description="Rethinking how we develop Africa's founders.",
                event_date=datetime(2026, 8, 31, 17, 0, tzinfo=timezone.utc),
                meeting_link="https://zoom.us/j/dummy4"
            )
        ]
        
        session.add_all(events)
        await session.commit()
        print("Events seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_events())
