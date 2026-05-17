"""API router for environment domain."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.environment.schemas import EnvironmentEntryCreate, EnvironmentEntryResponse
from app.environment.service import EnvironmentService

router = APIRouter(prefix="/environment", tags=["environment"])


@router.post("", response_model=EnvironmentEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: EnvironmentEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    return await EnvironmentService(db).create_entry(user.id, data)


@router.get("", response_model=list[EnvironmentEntryResponse])
async def list_entries(
    start: str | None = None,
    end: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    start_date = None
    end_date = None
    if start:
        from datetime import datetime
        start_date = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if end:
        from datetime import datetime
        end_date = datetime.fromisoformat(end.replace("Z", "+00:00"))
    
    return await EnvironmentService(db).list_entries(
        user_id=user.id, start_date=start_date, end_date=end_date, limit=limit, offset=offset
    )


@router.get("/{entry_id}", response_model=EnvironmentEntryResponse)
async def get_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    entry = await EnvironmentService(db).get_entry(user.id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Environment entry not found")
    return entry


@router.put("/{entry_id}", response_model=EnvironmentEntryResponse)
async def update_entry(
    entry_id: int,
    data: EnvironmentEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    entry = await EnvironmentService(db).update_entry(user.id, entry_id, data)
    if not entry:
        raise HTTPException(status_code=404, detail="Environment entry not found")
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    success = await EnvironmentService(db).delete_entry(user.id, entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Environment entry not found")
    return None