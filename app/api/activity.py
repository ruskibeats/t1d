from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.activity.schemas import ActivityEntryCreate, ActivityEntryResponse
from app.activity.service import ActivityService

route = APIRouter(prefix="/activity", tags=["Activity"])


@route.post("", response_model=ActivityEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(data: ActivityEntryCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_active_user)):
    return await ActivityService(db).create(user.id, data)


@route.get("", response_model=list[ActivityEntryResponse])
async def list_entries(limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db), user: User = Depends(require_active_user)):
    return await ActivityService(db).list(user_id=user.id, limit=limit, offset=offset)


@route.get("/{entry_id}", response_model=ActivityEntryResponse)
async def get_entry(entry_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_active_user)):
    entry = await ActivityService(db).get(user.id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Activity entry not found")
    return entry


@route.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(entry_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_active_user)):
    deleted = await ActivityService(db).delete(user.id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Activity entry not found")
