from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.heart.schemas import HeartRateEntryCreate, HeartRateEntryResponse
from app.heart.service import HeartRateService

route = APIRouter(prefix="/heart", tags=["Heart Rate"])


@route.post("", response_model=HeartRateEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: HeartRateEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    return await HeartRateService(db).create(user.id, data)


@route.get("", response_model=list[HeartRateEntryResponse])
async def list_entries(
    start: str | None = None,
    end: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    return await HeartRateService(db).list(user_id=user.id, limit=limit, offset=offset)


@route.get("/{entry_id}", response_model=HeartRateEntryResponse)
async def get_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    entry = await HeartRateService(db).get(user.id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Heart rate entry not found")
    return entry


@route.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    deleted = await HeartRateService(db).delete(user.id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Heart rate entry not found")
