from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_admin, get_current_user, get_optional_user
from app.database import get_db
from app.models import Event, EventBooking, User
from app.schemas import EventBookingOut, EventCreate, EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
@router.get("/")
async def list_events(
    request: Request,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
        return FileResponse("static/events.html", media_type="text/html")
    result = await db.execute(select(Event).order_by(Event.event_date.desc()))
    events = result.scalars().all()

    # Check which ones the current user has booked
    booked_event_ids = set()
    is_admin = False
    if current_user:
        booking_result = await db.execute(
            select(EventBooking.event_id).where(EventBooking.user_id == current_user.id)
        )
        booked_event_ids = set(booking_result.scalars().all())
        admin_roles = [
            "admin",
            "super_admin",
            "event_manager",
            "program_manager",
            "editor",
        ]
        is_admin = current_user.role in admin_roles

    response = []
    for e in events:
        is_booked = e.id in booked_event_ids
        can_access_links = is_booked or is_admin
        evt_dict = {
            "id": e.id,
            "title": e.title,
            "subtitle": e.subtitle,
            "description": e.description,
            "event_date": e.event_date,
            "meeting_link": e.meeting_link if can_access_links else None,
            "registration_link": e.registration_link,
            "recording_link": e.recording_link if can_access_links else None,
            "speaker_name": e.speaker_name,
            "speaker_bio": e.speaker_bio,
            "speaker_image_url": e.speaker_image_url,
            "price_display": e.price_display,
            "cover_image_url": e.cover_image_url,
            "created_at": e.created_at,
            "is_booked": is_booked,
        }
        response.append(evt_dict)

    return response


@router.post("/", response_model=EventOut, status_code=201)
async def create_event(
    event_in: EventCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    new_event = Event(**event_in.model_dump(exclude_unset=True))
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    return new_event


@router.post("/{event_id}/book", status_code=201)
async def book_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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

    booking = EventBooking(event_id=event_id, user_id=current_user.id)
    db.add(booking)
    await db.commit()
    return {"message": "Successfully booked the event"}


@router.get("/me/bookings", response_model=List[EventBookingOut])
async def my_event_bookings(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(EventBooking)
        .options(selectinload(EventBooking.event))
        .where(EventBooking.user_id == current_user.id)
        .order_by(EventBooking.booked_at.desc())
    )
    bookings = result.scalars().all()
    return bookings
