from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.exercise.schemas import ExerciseEntryCreate, ExerciseEntryResponse, ExerciseEntryWithSets, ExerciseEntrySetCreate, ExerciseEntrySetResponse
from app.exercise.service import ExerciseService

route = APIRouter(prefix="/exercise", tags=["exercise"])

@route.post("", response_model=ExerciseEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: ExerciseEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    return await ExerciseService(db).create(user.id, data)

@route.get("", response_model=list[ExerciseEntryResponse])
async def list_entries(
    start: str | None = None,
    end: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    return await ExerciseService(db).list(user_id=user.id, limit=limit, offset=offset, db=db)

@route.get("/{entry_id}", response_model=ExerciseEntryWithSets)
async def get_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    entry = await ExerciseService(db).get(user.id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Exercise entry not found")
    # Load sets
    sets = await ExerciseService(db).list_sets_for_entry(entry_id)
    # Manually combine for response (since we don't have a direct relationship in the model for the response)
    # We'll create a dict that matches the ExerciseEntryWithSets schema
    entry_dict = entry.__dict__
    entry_dict["sets"] = sets
    return ExerciseEntryWithSets(**entry_dict)

@route.post("/{entry_id}/sets", response_model=ExerciseEntrySetResponse, status_code=status.HTTP_201_CREATED)
async def create_set(entry_id: int, data: ExerciseEntrySetCreate, user: User = Depends(require_active_user), db: AsyncSession = Depends(get_db)):
    return await ExerciseService(db).create_set(entry_id, data)

@route.get("/{entry_id}/sets", response_model=list[ExerciseEntrySetResponse])
async def list_sets(entry_id: int, user: User = Depends(require_active_user), db: AsyncSession = Depends(get_db)):
    return await ExerciseService(db).list_sets_for_entry(entry_id)