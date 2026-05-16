from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.fasting.schemas import FastingEntryCreate, FastingEntryResponse
from app.fasting.service import FastingService

route = APIRouter(prefix="/fasting", tags=["fasting"])

@route.post("", response_model=FastingEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(data: FastingEntryCreate, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    return await FastingService(db).create_entry(user_id, data)

@route.get("", response_model=list[FastingEntryResponse])
async def list_entries(
    user_id: int = Query(..., ge=1), 
    limit: int = 100, 
    offset: int = 0,
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    from datetime import datetime
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    return await FastingService(db).list_entries(
        user_id=user_id, 
        limit=limit, 
        offset=offset,
        start_date=start,
        end_date=end
    )

@route.get("/{entry_id}", response_model=FastingEntryResponse)
async def get_entry(entry_id: int, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    entry = await FastingService(db).get_entry(user_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Fasting entry not found")
    return entry

@route.put("/{entry_id}", response_model=FastingEntryResponse)
async def update_entry(entry_id: int, data: FastingEntryCreate, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    entry = await FastingService(db).update_entry(user_id, entry_id, data)
    if not entry:
        raise HTTPException(status_code=404, detail="Fasting entry not found")
    return entry

@route.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(entry_id: int, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    success = await FastingService(db).delete_entry(user_id, entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Fasting entry not found")

@route.get("/active", response_model=FastingEntryResponse)
async def get_active_fast(user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    active = await FastingService(db).get_active_fast(user_id)
    if not active:
        raise HTTPException(status_code=404, detail="No active fasting entry found")
    return active