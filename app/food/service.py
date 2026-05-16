"""Service layer for food domain with multi-provider search."""

from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.food.models import Food, FoodEntry
from app.food.schemas import FoodCreate, FoodEntryCreate


class FoodService:
    """Service for CRUD operations on foods and food entries.

    Includes multi-provider food search that queries personal foods,
    OpenFoodFacts, and USDA FoodData Central.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Food CRUD
    # ------------------------------------------------------------------

    async def create_food(self, user_id: int, data: FoodCreate) -> Food:
        food = Food(user_id=user_id, **data.model_dump())
        self.db.add(food)
        await self.db.flush()
        await self.db.refresh(food)
        return food

    async def get_food(self, user_id: int, food_id: int) -> Optional[Food]:
        result = await self.db.execute(
            select(Food).where(Food.user_id == user_id, Food.id == food_id)
        )
        return result.scalar_one_or_none()

    async def list_foods(self, user_id: int, limit: int = 50, offset: int = 0):
        result = await self.db.execute(
            select(Food)
            .where(Food.user_id == user_id)
            .order_by(desc(Food.updated_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_foods(self, user_id: int, query: str, limit: int = 20):
        result = await self.db.execute(
            select(Food).where(
                Food.user_id == user_id,
                Food.name.ilike(f"%{query}%"),
            ).limit(limit)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Multi-Provider Food Search (P5-04)
    # ------------------------------------------------------------------

    async def search_all_providers(
        self,
        user_id: int,
        query: str,
        limit: int = 20,
        include_personal: bool = True,
        include_openfoodfacts: bool = True,
        include_usda: bool = True,
    ) -> list[Food]:
        """Search across all food providers, with personal foods ranked first.

        Args:
            user_id: User ID for personal food results.
            query: Search term.
            limit: Maximum results across all providers.
            include_personal: Whether to search user's personal foods table.
            include_openfoodfacts: Whether to search OpenFoodFacts.
            include_usda: Whether to search USDA FoodData Central.

        Returns:
            List of Food objects. Personal results are ranked first.
        """
        results: list[Food] = []

        # 1. Personal foods (highest priority)
        if include_personal:
            personal = await self.search_foods(user_id, query, limit=limit)
            results.extend(personal)

        # 2. OpenFoodFacts
        if include_openfoodfacts and len(results) < limit:
            try:
                from app.food.providers import openfoodfacts as off
                batch = await off.search_by_name(query, limit=limit)
                for fc in batch:
                    if len(results) >= limit:
                        break
                    results.append(self._provider_to_food(user_id, fc))
            except Exception:
                pass

        # 3. USDA FoodData Central
        if include_usda and len(results) < limit:
            try:
                from app.food.providers import usda
                batch = await usda.search_by_name(query, limit=limit)
                for fc in batch:
                    if len(results) >= limit:
                        break
                    results.append(self._provider_to_food(user_id, fc))
            except Exception:
                pass

        return results[:limit]

    def _provider_to_food(self, user_id: int, fc: FoodCreate) -> Food:
        """Convert a FoodCreate from an external provider into a transient Food object."""
        return Food(
            id=0,
            user_id=user_id,
            name=fc.name or "Unknown",
            brand_name=fc.brand_name,
            serving_size=fc.serving_size,
            serving_unit=fc.serving_unit or "g",
            calories=fc.calories,
            protein=fc.protein,
            carbs=fc.carbs,
            fat=fc.fat,
            fiber=fc.fiber,
            sugars=fc.sugars,
            sodium=fc.sodium,
            barcode=fc.barcode,
            source=fc.source or "external",
        )

    # ------------------------------------------------------------------
    # Food Entry CRUD
    # ------------------------------------------------------------------

    async def create_entry(self, user_id: int, data: FoodEntryCreate) -> FoodEntry:
        entry = FoodEntry(user_id=user_id, **data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def list_entries(
        self,
        user_id: int,
        start_date=None,
        end_date=None,
        meal_type: Optional[str] = None,
        limit: int = 100,
    ):
        stmt = select(FoodEntry).where(FoodEntry.user_id == user_id)
        if start_date:
            stmt = stmt.where(FoodEntry.entry_date >= start_date)
        if end_date:
            stmt = stmt.where(FoodEntry.entry_date <= end_date)
        stmt = stmt.order_by(desc(FoodEntry.entry_date))
        if meal_type:
            stmt = stmt.where(FoodEntry.meal_type == meal_type)
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
