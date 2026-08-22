from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from app.database import get_db
from app.models import Season, SeasonSession, User
from app.schemas import SeasonCreate, SeasonUpdate, SeasonOut, SeasonSessionCreate, SeasonSessionOut
from app.auth import get_current_admin, get_optional_user

router = APIRouter(prefix="/seasons", tags=["seasons"])

@router.get("/", response_model=List[SeasonOut])
async def list_seasons(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Season).order_by(Season.start_date.desc()))
    return result.scalars().all()

@router.post("/", response_model=SeasonOut, status_code=201)
async def create_season(
    season_in: SeasonCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    season = Season(**season_in.dict())
    db.add(season)
    await db.commit()
    await db.refresh(season)
    return season

@router.get("/{season_id}", response_model=SeasonOut)
async def get_season(season_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Season).where(Season.id == season_id))
    season = result.scalars().first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    return season

@router.put("/{season_id}", response_model=SeasonOut)
async def update_season(
    season_id: str,
    season_in: SeasonUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Season).where(Season.id == season_id))
    season = result.scalars().first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    
    update_data = season_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(season, key, value)
    
    await db.commit()
    await db.refresh(season)
    return season

@router.get("/{season_id}/sessions", response_model=List[SeasonSessionOut])
async def list_season_sessions(season_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SeasonSession)
        .where(SeasonSession.season_id == season_id)
        .order_by(SeasonSession.session_number)
    )
    return result.scalars().all()

@router.post("/{season_id}/sessions", response_model=SeasonSessionOut, status_code=201)
async def create_season_session(
    season_id: str,
    session_in: SeasonSessionCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    season_result = await db.execute(select(Season).where(Season.id == season_id))
    if not season_result.scalars().first():
        raise HTTPException(status_code=404, detail="Season not found")
        
    session = SeasonSession(**session_in.dict(), season_id=season_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session
