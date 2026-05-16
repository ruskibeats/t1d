from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.food.schemas import FoodCreate, FoodResponse, FoodEntryCreate, FoodEntryResponse
from app.food.service import FoodService

route = APIRouter(prefix="/food", tags=["food"])

@route.post("", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
async def create_food(data: FoodCreate, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    return await FoodService(db).create_food(user_id, data)

@route.get("", response_model=list[FoodResponse])
async def list_foods(user_id: int = Query(..., ge=1), limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    return await FoodService(db).list_foods(user_id, limit, offset)

@route.get("/search", response_model=list[FoodResponse])
async def search_foods(q: str, user_id: int = Query(..., ge=1), limit: int = 20, db: AsyncSession = Depends(get_db)):
    return await FoodService(db).search_foods(user_id, q, limit)

@route.post("/entries", response_model=FoodEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(data: FoodEntryCreate, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    return await FoodService(db).create_entry(user_id, data)

@route.get("/entries", response_model=list[FoodEntryResponse])
async def list_entries(user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    return await FoodService(db).list_entries(user_id, limit=100)
