from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime, timezone

from app.database import get_db
from app.models import Event, EventBooking, User
from app.schemas import EventCreate, EventOut, EventBookingOut
from app.auth import get_current_user, get_current_admin, get_optional_user

router = APIRouter(prefix="/events", tags=["events"])

@router.get("/", response_model=List[EventOut])
async def list_events(current_user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Event).order_by(Event.event_date.desc())
    )
    events = result.scalars().all()

    # Check which ones the current user has booked
    booked_event_ids = set()
    if current_user:
        booking_result = await db.execute(
            select(EventBooking.event_id).where(EventBooking.user_id == current_user.id)
        )
        booked_event_ids = set(booking_result.scalars().all())

    response = []
    for e in events:
        evt_dict = {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "event_date": e.event_date,
            "meeting_link": e.meeting_link,
            "registration_link": e.registration_link,
            "recording_link": e.recording_link,
            "created_at": e.created_at,
            "is_booked": e.id in booked_event_ids
        }
        response.append(evt_dict)

    return response

@router.post("/", response_model=EventOut, status_code=201)
async def create_event(
    event_in: EventCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    new_event = Event(
        title=event_in.title,
        description=event_in.description,
        event_date=event_in.event_date,
        meeting_link=event_in.meeting_link
    )
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    return new_event

@router.post("/{event_id}/book", status_code=201)
async def book_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    result = await db.execute(
        select(EventBooking)
        .where(EventBooking.event_id == event_id)
        .where(EventBooking.user_id == current_user.id)
    )
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Already booked for this event")
        
    booking = EventBooking(
        event_id=event_id,
        user_id=current_user.id
    )
    db.add(booking)
    await db.commit()
    return {"message": "Successfully booked the event"}

@router.get("/me/bookings", response_model=List[EventBookingOut])
async def my_event_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(EventBooking)
        .options(selectinload(EventBooking.event))
        .where(EventBooking.user_id == current_user.id)
        .order_by(EventBooking.booked_at.desc())
    )
    bookings = result.scalars().all()
    return bookings
