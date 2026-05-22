from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.food.schemas import FoodCreate, FoodResponse, FoodEntryCreate, FoodEntryResponse, MealImpactRequest, MealImpactResponse
from app.food.service import FoodService

route = APIRouter(prefix="/food", tags=["food"])

@route.post("", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
async def create_food(
    data: FoodCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    return await FoodService(db).create_food(user.id, data)

@route.get("", response_model=list[FoodResponse])
async def list_foods(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    return await FoodService(db).list_foods(user.id, limit, offset)

@route.get("/search", response_model=list[FoodResponse])
async def search_foods(
    q: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    return await FoodService(db).search_foods(user.id, q, limit)

@route.post("/entries", response_model=FoodEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: FoodEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    return await FoodService(db).create_entry(user.id, data)

@route.get("/entries", response_model=list[FoodEntryResponse])
async def list_entries(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    return await FoodService(db).list_entries(user.id, limit=100)


@route.post("/meal-impact", response_model=MealImpactResponse)
async def estimate_meal_impact(
    data: MealImpactRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    """Estimate likely glucose impact for a proposed meal."""
    try:
        return await FoodService(db).estimate_meal_impact(
            user_id=user.id,
            items=data.items,
            eaten_at=data.eaten_at,
            limit_per_item=data.limit_per_item,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
