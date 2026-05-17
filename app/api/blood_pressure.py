from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.blood_pressure.schemas import BloodPressureEntryCreate, BloodPressureEntryResponse
from app.blood_pressure.service import BloodPressureService

route = APIRouter(prefix="/blood-pressure", tags=["Blood Pressure"])


@route.post("", response_model=BloodPressureEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(data: BloodPressureEntryCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_active_user)):
    return await BloodPressureService(db).create(user.id, data)


@route.get("", response_model=list[BloodPressureEntryResponse])
async def list_entries(limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db), user: User = Depends(require_active_user)):
    return await BloodPressureService(db).list(user_id=user.id, limit=limit, offset=offset)


@route.get("/{entry_id}", response_model=BloodPressureEntryResponse)
async def get_entry(entry_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_active_user)):
    entry = await BloodPressureService(db).get(user.id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Blood pressure entry not found")
    return entry


@route.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(entry_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_active_user)):
    deleted = await BloodPressureService(db).delete(user.id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Blood pressure entry not found")
