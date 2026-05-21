from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.sleep.schemas import SleepEntryCreate, SleepEntryResponse, SleepEntryWithStages, SleepStageCreate, SleepStageResponse
from app.sleep.service import SleepService

route = APIRouter(prefix="/sleep", tags=["sleep"])

@route.post("", response_model=SleepEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(data: SleepEntryCreate, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    return await SleepService(db).create(user_id, data)

@route.get("", response_model=list[SleepEntryResponse])
async def list_entries(user_id: int = Query(..., ge=1), limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db)):
    return await SleepService(db).list(user_id=user_id, limit=limit, offset=offset, db=db)

@route.get("/{entry_id}", response_model=SleepEntryWithStages)
async def get_entry(entry_id: int, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    entry = await SleepService(db).get(user_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Sleep entry not found")
    # Load stages
    stages = await SleepService(db).list_stages_for_entry(entry_id)
    # Manually combine for response
    entry_dict = entry.__dict__
    entry_dict["stages"] = stages
    return SleepEntryWithStages(**entry_dict)

@route.post("/{entry_id}/stages", response_model=SleepStageResponse, status_code=status.HTTP_201_CREATED)
async def create_stage(entry_id: int, data: SleepStageCreate, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    return await SleepService(db).create_stage(entry_id, data)

@route.get("/{entry_id}/stages", response_model=list[SleepStageResponse])
async def list_stages(entry_id: int, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    return await SleepService(db).list_stages_for_entry(entry_id)