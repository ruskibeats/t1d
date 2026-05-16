"""FastAPI routes for water tracking domain."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.water.schemas import WaterEntryCreate, WaterEntryResponse
from app.water.service import WaterService

route = APIRouter(prefix="/water", tags=["Water"])


@route.post("", response_model=WaterEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_water(
    data: WaterEntryCreate,
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    return await WaterService(db).create(user_id, data)


@route.get("", response_model=list[WaterEntryResponse])
async def list_water(
    user_id: int = Query(..., ge=1),
    start: datetime = Query(default=None),
    end: datetime = Query(default=None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await WaterService(db).list(user_id, start, end, limit)


@route.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_water(
    entry_id: int,
    user_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    deleted = await WaterService(db).delete(user_id, entry_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Water entry not found")
