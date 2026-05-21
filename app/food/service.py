"""Service layer for food domain with multi-provider search."""

from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.food.models import Food, FoodEntry
from app.food.schemas import FoodCreate, FoodEntryCreate
from app.metrics.types import MetricType
from app.services.metric_registry import MetricRegistry


def _parse_serving_size(value: str | float | None) -> float | None:
    """Parse serving size string into a float.
    
    OpenFoodFacts returns values like "100 g" or "1 cup (240ml)".
    Extract the leading number.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    import re
    match = re.match(r"(\d+\.?\d*)", str(value).strip())
    if match:
        return float(match.group(1))
    return None


class FoodService:
    """Service for CRUD operations on foods and food entries.

    Includes multi-provider food search that queries personal foods,
    OpenFoodFacts, and USDA FoodData Central.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._metric_registry = MetricRegistry(db)

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
    # Multi-Provider Food Search
    # ------------------------------------------------------------------

    async def _search_local_foods(self, user_id: int, query: str, limit: int = 10):
        """Search only the local Food table. Returns list of Food ORM objects."""
        from app.food.models import Food
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(Food).where(
                Food.user_id == user_id,
                Food.name.ilike(f"%{query}%"),
            ).limit(limit)
        )
        return list(result.scalars().all())

    async def search_external_foods(
        self,
        session: AsyncSession,
        user_id: int,
        query: str,
        use_external: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search for foods across local DB and external providers.
        
        Priority: local DB → OpenFoodFacts → USDA
        External results are cached in the local Food table.
        
        Returns list of dicts with normalized nutrition fields.
        """
        from app.food.models import Food
        from sqlalchemy import select
        
        results = []
        
        # 1. Search local DB
        local = await session.execute(
            select(Food).where(
                Food.user_id == user_id,
                Food.name.ilike(f"%{query}%"),
            ).limit(10)
        )
        for food in local.scalars():
            results.append({
                "source": "local",
                "name": food.name,
                "carbs_per_100g": food.carbs,
                "protein_per_100g": food.protein,
                "fat_per_100g": food.fat,
                "calories_per_100g": food.calories,
                "serving_size": food.serving_size,
            })
        
        if not use_external:
            return results
        
        # 2. Search OpenFoodFacts
        from app.food.providers.openfoodfacts import OpenFoodFactsClient
        off_client = OpenFoodFactsClient()
        off_results = await off_client.search_by_name(query, page_size=5)
        
        for product in off_results:
            results.append({
                "source": "openfoodfacts",
                "name": product.name,
                "brand": product.brand,
                "barcode": product.barcode,
                "carbs_per_100g": product.carbs_per_100g,
                "protein_per_100g": product.protein_per_100g,
                "fat_per_100g": product.fat_per_100g,
                "calories_per_100g": product.calories_per_100g,
                "serving_size": product.serving_size,
            })
            
            # Cache in local DB
            cached = Food(
                user_id=user_id,
                name=product.name,
                brand_name=product.brand,
                barcode=product.barcode,
                carbs=product.carbs_per_100g,
                protein=product.protein_per_100g,
                fat=product.fat_per_100g,
                calories=product.calories_per_100g,
                serving_size=_parse_serving_size(product.serving_size),
                source="openfoodfacts",
            )
            session.add(cached)
        
        # 3. Search USDA (if API key configured)
        from app.food.providers.usda import USDAClient
        usda_client = USDAClient()
        if usda_client.api_key:
            usda_results = await usda_client.search_by_name(query, page_size=5)
            
            for item in usda_results:
                results.append({
                    "source": "usda",
                    "name": item.name,
                    "brand": item.brand,
                    "fdc_id": item.fdc_id,
                    "carbs_per_100g": item.carbs_per_100g,
                    "protein_per_100g": item.protein_per_100g,
                    "fat_per_100g": item.fat_per_100g,
                    "calories_per_100g": item.calories_per_100g,
                    "serving_size": item.serving_size,
                })
        
        if results:
            await session.commit()
        
        return results

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
            personal = await self._search_local_foods(user_id, query, limit=limit)
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
        # Dual-write via consolidated registry (batch metrics via single call)
        await self._metric_registry.record_metrics_batch(
            user_id=user_id,
            measured_at=entry.entry_date,
            source=entry.source,
            metrics=[
                {"metric_type": MetricType.CALORIES, "value": entry.calories, "unit": "kcal"},
                {"metric_type": MetricType.PROTEIN, "value": entry.protein, "unit": "g"},
                {"metric_type": MetricType.CARBS, "value": entry.carbs, "unit": "g"},
                {"metric_type": MetricType.FAT, "value": entry.fat, "unit": "g"},
                {"metric_type": MetricType.FIBER, "value": entry.fiber, "unit": "g"},
                {"metric_type": MetricType.GLYCEMIC_LOAD, "value": entry.glycemic_load, "unit": "score"},
            ]
        )
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