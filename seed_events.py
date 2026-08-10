import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal, engine, Base
from app.models import Event
from datetime import datetime, timedelta, timezone

async def seed_events():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        # Find next Monday
        today = datetime.now(timezone.utc)
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0: # Target next Monday
            days_ahead += 7
        
        next_monday = today + timedelta(days=days_ahead)
        next_monday = next_monday.replace(hour=18, minute=0, second=0, microsecond=0) # 6 PM

        event1 = Event(
            title="Monday Masterclass: Vision & Focus",
            description="Join us for a powerful masterclass focusing on building an unshakeable mindset.",
            event_date=next_monday,
            meeting_link="https://zoom.us/j/dummy123"
        )
        
        event2 = Event(
            title="Monday Masterclass: Navigating Tech",
            description="Learn how to leverage AI and Tech to scale your influence.",
            event_date=next_monday + timedelta(days=7),
            meeting_link="https://zoom.us/j/dummy456"
        )
        
        session.add_all([event1, event2])
        await session.commit()
        print("Events seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_events())
