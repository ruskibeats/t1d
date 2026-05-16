"""FastAPI routes for mood domain."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.mood.schemas import MoodEntryCreate, MoodEntryResponse
from app.mood.service import MoodService

route = APIRouter(prefix="/mood", tags=["Mood"])


@route.post("", response_model=MoodEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_mood(
    data: MoodEntryCreate,
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    return await MoodService(db).create(user_id, data)


@route.get("", response_model=list[MoodEntryResponse])
async def list_mood(
    user_id: int = Query(..., ge=1),
    start: datetime = Query(default=None),
    end: datetime = Query(default=None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await MoodService(db).list(user_id, start, end, limit)


@route.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mood(
    entry_id: int,
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    deleted = await MoodService(db).delete(user_id, entry_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mood entry not found")
