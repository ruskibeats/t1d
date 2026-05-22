"""Service layer for food domain with multi-provider search."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContextEvent, GlucoseReading
from app.metrics.models import HealthMetric
from app.food.models import Food, FoodEntry, OpenFoodFactsProduct
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
    gram_matches = re.findall(r"(\d+\.?\d*)\s*g\b", str(value), flags=re.IGNORECASE)
    if gram_matches:
        return float(gram_matches[-1])
    match = re.match(r"(\d+\.?\d*)", str(value).strip())
    if match:
        return float(match.group(1))
    return None


def _safe_float(value: Any) -> float | None:
    """Convert a value to float when possible."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_or_none(value: float | None, digits: int = 1) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _as_naive_utc(value: datetime) -> datetime:
    """Match existing DB convention for timestamp-without-timezone columns."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


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

    async def _search_local_off(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search the local Open Food Facts Postgres table.
        
        Queries openfoodfacts_products table for matching products.
        Uses trigram similarity on product_name for fuzzy matching.
        
        Returns list of dicts with normalized nutrition fields matching
        the OpenFoodFactsProduct response shape.
        """
        results = []
        
        # Use name similarity search - trigram index should be available in Postgres
        # For SQLite compatibility, fall back to ILIKE
        stmt = (
            select(OpenFoodFactsProduct)
            .where(
                OpenFoodFactsProduct.product_name.isnot(None),
                OpenFoodFactsProduct.carbs_100g.isnot(None),  # Only products with nutrition data
            )
            .order_by(
                func.similarity(OpenFoodFactsProduct.product_name, query).desc(),
                OpenFoodFactsProduct.nutriscore_score.asc().nullslast(),  # Better nutrition scores first
            )
            .limit(limit)
        )
        
        try:
            result = await self.db.execute(stmt)
            products = list(result.scalars().all())
            
            for product in products:
                results.append({
                    "source": "openfoodfacts_local",
                    "name": product.product_name,
                    "brand": product.brands,
                    "barcode": product.code,
                    "carbs_per_100g": product.carbs_100g,
                    "protein_per_100g": product.proteins_100g,
                    "fat_per_100g": product.fat_100g,
                    "calories_per_100g": product.energy_kcal_100g,
                    "serving_size": product.serving_size,
                    "fiber_per_100g": product.fiber_100g,
                    "sugars_per_100g": product.sugars_100g,
                    "sodium_per_100g": product.sodium_100g,
                })
        except Exception:
            # Fallback for databases without pg_trgm extension or similarity function
            # Use tokenized ILIKE search as fallback so "large fries" can match
            # product names such as "Large French Fries".
            terms = [term for term in query.replace("-", " ").split() if term]
            name_conditions = [
                OpenFoodFactsProduct.product_name.ilike(f"%{term}%")
                for term in terms
            ] or [OpenFoodFactsProduct.product_name.ilike(f"%{query}%")]
            stmt = (
                select(OpenFoodFactsProduct)
                .where(
                    and_(*name_conditions),
                    OpenFoodFactsProduct.carbs_100g.isnot(None),
                )
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            products = list(result.scalars().all())
            
            for product in products:
                results.append({
                    "source": "openfoodfacts_local",
                    "name": product.product_name,
                    "brand": product.brands,
                    "barcode": product.code,
                    "carbs_per_100g": product.carbs_100g,
                    "protein_per_100g": product.proteins_100g,
                    "fat_per_100g": product.fat_100g,
                    "calories_per_100g": product.energy_kcal_100g,
                    "serving_size": product.serving_size,
                    "fiber_per_100g": product.fiber_100g,
                    "sugars_per_100g": product.sugars_100g,
                    "sodium_per_100g": product.sodium_100g,
                })
        
        return results

    async def search_external_foods(
        self,
        session: AsyncSession,
        user_id: int,
        query: str,
        use_external: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search for foods across local DB and external providers.
        
        Priority: local DB → local OpenFoodFacts (Postgres) → online OpenFoodFacts → USDA
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
                "brand": food.brand_name,
                "barcode": food.barcode,
                "carbs_per_100g": food.carbs,
                "protein_per_100g": food.protein,
                "fat_per_100g": food.fat,
                "calories_per_100g": food.calories,
                "serving_size": food.serving_size,
            })
        
        if not use_external:
            return results
        
        # 2. Search local OpenFoodFacts (Postgres) - before online API
        local_off_results = await self._search_local_off(query, limit=5)
        for product in local_off_results:
            results.append(product)
            # Note: local OFF products are already in the lookup table,
            # no need to cache them again in foods table
        
        # 3. Search online OpenFoodFacts API as fallback if local OFF has no results
        if not local_off_results:
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
        
        # 4. Search USDA (if API key configured)
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

        Priority: personal foods → local OpenFoodFacts (Postgres) → online OpenFoodFacts → USDA
        
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

        # 2. Local OpenFoodFacts (Postgres) lookup
        if include_openfoodfacts and len(results) < limit:
            try:
                local_off = await self._search_local_off(query, limit=limit)
                for product in local_off:
                    if len(results) >= limit:
                        break
                    # Convert local OFF result to Food object for consistent return type
                    food = Food(
                        id=0,
                        user_id=user_id,
                        name=product["name"],
                        brand_name=product.get("brand"),
                        barcode=product.get("barcode"),
                        serving_size=_parse_serving_size(product.get("serving_size")),
                        serving_unit="g",
                        calories=product.get("calories_per_100g"),
                        protein=product.get("protein_per_100g"),
                        carbs=product.get("carbs_per_100g"),
                        fat=product.get("fat_per_100g"),
                        fiber=product.get("fiber_per_100g"),
                        sugars=product.get("sugars_per_100g"),
                        sodium=product.get("sodium_per_100g"),
                        source="openfoodfacts_local",
                    )
                    results.append(food)
            except Exception:
                pass

        # 3. Online OpenFoodFacts API as fallback (only if local OFF had no results)
        if include_openfoodfacts and len(results) < limit and not any(
            f.source == "openfoodfacts_local" for f in results
        ):
            try:
                from app.food.providers import openfoodfacts as off
                batch = await off.search_by_name(query, limit=limit)
                for fc in batch:
                    if len(results) >= limit:
                        break
                    results.append(self._provider_to_food(user_id, fc))
            except Exception:
                pass

        # 4. USDA FoodData Central
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
    # Meal Impact Forecast
    # ------------------------------------------------------------------

    async def estimate_meal_impact(
        self,
        user_id: int,
        items: list[str],
        eaten_at: datetime | None = None,
        limit_per_item: int = 5,
    ) -> dict[str, Any]:
        """Estimate the likely glucose impact of a proposed meal.

        This is rules-based decision support. It combines local nutrition
        lookup, recent glucose trend, and recent insulin/exercise context; it
        does not recommend insulin doses.
        """
        if not items:
            raise ValueError("At least one meal item is required.")

        eaten_at = _as_naive_utc(eaten_at or datetime.now(timezone.utc))
        matched_items = []
        unmatched_items = []

        for item in items:
            candidates = await self._search_local_off(item, limit=limit_per_item)
            selected = self._select_best_meal_candidate(item, candidates)
            if selected is None:
                unmatched_items.append(item)
                continue
            matched_items.append(self._meal_candidate_to_impact_item(item, selected))

        totals = self._meal_impact_totals(matched_items)
        glucose_context = await self._recent_glucose_context(user_id, eaten_at)
        recent_context = await self._recent_meal_context(user_id, eaten_at)
        risk = self._meal_impact_risk(totals, glucose_context, recent_context, unmatched_items)

        return {
            "question": f"Can I eat {' and '.join(items)} now?",
            "eaten_at": eaten_at.isoformat(),
            "matched_items": matched_items,
            "unmatched_items": unmatched_items,
            "meal_totals": totals,
            "glucose_context": glucose_context,
            "recent_context": recent_context,
            "forecast": risk,
            "safety_note": (
                "This is educational decision support, not dosing advice. "
                "Use your prescribed insulin plan and check live CGM/fingerstick data."
            ),
        }

    def _select_best_meal_candidate(self, query: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not candidates:
            return None

        query_terms = [term for term in query.lower().replace("-", " ").split() if term]

        def score(candidate: dict[str, Any]) -> tuple[int, float]:
            name = str(candidate.get("name") or "").lower()
            brand = str(candidate.get("brand") or "").lower()
            text = f"{name} {brand}"
            term_hits = sum(1 for term in query_terms if term in text)
            has_serving = 1 if candidate.get("serving_size") else 0
            nutrition_count = sum(
                1
                for key in ("carbs_per_100g", "fat_per_100g", "protein_per_100g", "calories_per_100g")
                if candidate.get(key) is not None
            )
            return (term_hits + has_serving + nutrition_count, -len(name))

        return max(candidates, key=score)

    def _meal_candidate_to_impact_item(self, query: str, candidate: dict[str, Any]) -> dict[str, Any]:
        serving_g = self._assumed_serving_grams(query, candidate.get("serving_size"))

        def grams_from_100g(key: str) -> float | None:
            value = _safe_float(candidate.get(key))
            if value is None:
                return None
            return value * serving_g / 100.0

        return {
            "query": query,
            "name": candidate.get("name"),
            "brand": candidate.get("brand"),
            "barcode": candidate.get("barcode"),
            "serving_size": candidate.get("serving_size"),
            "assumed_serving_g": _round_or_none(serving_g),
            "carbs_g": _round_or_none(grams_from_100g("carbs_per_100g")),
            "sugars_g": _round_or_none(grams_from_100g("sugars_per_100g")),
            "fiber_g": _round_or_none(grams_from_100g("fiber_per_100g")),
            "protein_g": _round_or_none(grams_from_100g("protein_per_100g")),
            "fat_g": _round_or_none(grams_from_100g("fat_per_100g")),
            "calories": _round_or_none(grams_from_100g("calories_per_100g")),
            "per_100g": {
                "carbs": candidate.get("carbs_per_100g"),
                "sugars": candidate.get("sugars_per_100g"),
                "fiber": candidate.get("fiber_per_100g"),
                "protein": candidate.get("protein_per_100g"),
                "fat": candidate.get("fat_per_100g"),
                "calories": candidate.get("calories_per_100g"),
            },
        }

    def _assumed_serving_grams(self, query: str, serving_size: Any) -> float:
        serving_g = _parse_serving_size(serving_size) or 100.0
        normalized_query = query.lower()

        # OFF often stores restaurant fries as a generic 100g serving even when
        # the user asks for a large portion. Use a conservative fast-food style
        # estimate so impact questions do not undercount the meal.
        if "fries" in normalized_query and "large" in normalized_query:
            return max(serving_g, 150.0)
        if "fries" in normalized_query and "medium" in normalized_query:
            return max(serving_g, 115.0)
        if "fries" in normalized_query and "small" in normalized_query:
            return max(serving_g, 75.0)
        return serving_g

    def _meal_impact_totals(self, matched_items: list[dict[str, Any]]) -> dict[str, Any]:
        def total(key: str) -> float | None:
            values = [_safe_float(item.get(key)) for item in matched_items]
            values = [value for value in values if value is not None]
            return _round_or_none(sum(values)) if values else None

        carbs = total("carbs_g")
        fiber = total("fiber_g")
        fat = total("fat_g")
        protein = total("protein_g")
        calories = total("calories")
        net_carbs = carbs - fiber if carbs is not None and fiber is not None else carbs

        return {
            "items_matched": len(matched_items),
            "carbs_g": carbs,
            "net_carbs_g": _round_or_none(net_carbs),
            "sugars_g": total("sugars_g"),
            "fiber_g": fiber,
            "protein_g": protein,
            "fat_g": fat,
            "calories": calories,
            "is_high_carb": bool(carbs is not None and carbs >= 60),
            "is_high_fat": bool(fat is not None and fat >= 25),
            "is_high_protein": bool(protein is not None and protein >= 30),
        }

    async def _recent_glucose_context(self, user_id: int, at_time: datetime) -> dict[str, Any]:
        window_start = at_time - timedelta(hours=3)
        result = await self.db.execute(
            select(GlucoseReading)
            .where(
                GlucoseReading.user_id == user_id,
                GlucoseReading.timestamp >= window_start,
                GlucoseReading.timestamp <= at_time,
            )
            .order_by(GlucoseReading.timestamp.desc())
            .limit(24)
        )
        readings = list(result.scalars().all())
        if not readings:
            return {
                "latest_value": None,
                "latest_timestamp": None,
                "trend": "unknown",
                "trend_rate_mgdl_per_min": None,
                "summary": "No recent glucose data found.",
            }

        latest = readings[0]
        older = readings[-1] if len(readings) > 1 else None
        trend_rate = latest.trend_rate
        trend = latest.trend or "unknown"
        if trend_rate is None and older is not None:
            minutes = (latest.timestamp - older.timestamp).total_seconds() / 60
            if minutes > 0:
                trend_rate = (latest.glucose_value - older.glucose_value) / minutes
                if trend_rate >= 1.5:
                    trend = "rising_fast"
                elif trend_rate >= 0.5:
                    trend = "rising"
                elif trend_rate <= -1.5:
                    trend = "falling_fast"
                elif trend_rate <= -0.5:
                    trend = "falling"
                else:
                    trend = "flat"

        # Get personal patterns (historical norms for this time of day)
        personal_patterns = await self._get_personal_glucose_patterns(user_id, at_time)

        return {
            "latest_value": _round_or_none(latest.glucose_value, 0),
            "latest_timestamp": latest.timestamp.isoformat(),
            "trend": trend,
            "trend_rate_mgdl_per_min": _round_or_none(trend_rate, 2),
            "readings_considered": len(readings),
            "personal_patterns": personal_patterns,
            "summary": self._glucose_context_summary(latest.glucose_value, trend),
        }

    async def _get_personal_glucose_patterns(self, user_id: int, at_time: datetime) -> dict[str, Any]:
        """Get personal glucose patterns for this time of day from historical data.
        
        Uses health_metrics table to find patterns like:
        - Time-of-day baseline (dawn phenomenon)
        - Typical meal response curves
        - Recent variability
        """
        hour = at_time.hour
        
        # Query health_metrics for this user's historical patterns by hour using SQLAlchemy
        result = await self.db.execute(
            select(
                func.extract('hour', HealthMetric.measured_at).label('hour'),
                func.count().label('count'),
                func.round(func.avg(HealthMetric.value), 1).label('avg_value'),
                func.round(func.min(HealthMetric.value), 1).label('min_value'),
                func.round(func.max(HealthMetric.value), 1).label('max_value'),
            )
            .where(
                HealthMetric.user_id == user_id,
                HealthMetric.type == 'blood_glucose',
                HealthMetric.measured_at >= at_time - timedelta(days=30),
            )
            .group_by(func.extract('hour', HealthMetric.measured_at))
            .order_by('hour')
        )
        
        hour_patterns = {}
        for row in result.fetchall():
            hour_patterns[str(int(row[0]))] = {
                "count": row[1], 
                "avg": float(row[2]) if row[2] else None, 
                "min": float(row[3]) if row[3] else None, 
                "max": float(row[4]) if row[4] else None
            }
        
        # Get this hour's pattern specifically
        hour_pattern = hour_patterns.get(str(hour))
        
        return {
            "hour": hour,
            "baseline_historical_avg": hour_pattern.get("avg") if hour_pattern else None,
            "baseline_historical_min": hour_pattern.get("min") if hour_pattern else None,
            "baseline_historical_max": hour_pattern.get("max") if hour_pattern else None,
            "pattern_note": "Historical values from health_metrics for this hour of day" if hour_pattern else "No historical patterns available for this time"
        }

    def _glucose_context_summary(self, latest_value: float, trend: str) -> str:
        if latest_value < 70:
            return "Glucose is currently low; eating may be appropriate but confirm with your care plan."
        if latest_value > 180 and "rising" in trend:
            return "Glucose is already high and rising, so this meal is higher risk right now."
        if latest_value > 180:
            return "Glucose is above range; this meal may extend time high."
        if "falling" in trend:
            return "Glucose is falling; timing and fast carbs matter more than usual."
        if "rising" in trend:
            return "Glucose is rising; expect extra upward pressure from the meal."
        return "Glucose context is relatively steady based on recent readings."

    async def _recent_meal_context(self, user_id: int, at_time: datetime) -> dict[str, Any]:
        window_start = at_time - timedelta(hours=4)
        result = await self.db.execute(
            select(ContextEvent)
            .where(
                ContextEvent.user_id == user_id,
                ContextEvent.timestamp >= window_start,
                ContextEvent.timestamp <= at_time,
                ContextEvent.event_type.in_(["meal", "insulin", "exercise"]),
            )
            .order_by(ContextEvent.timestamp.desc())
            .limit(12)
        )
        events = list(result.scalars().all())
        return {
            "events_considered": len(events),
            "recent_insulin": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "insulin_units": event.insulin_units,
                    "insulin_type": event.insulin_type,
                }
                for event in events
                if event.event_type == "insulin"
            ],
            "recent_exercise": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "duration": event.duration,
                    "intensity": event.intensity,
                }
                for event in events
                if event.event_type == "exercise"
            ],
            "recent_meals": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "carbs_grams": event.carbs_grams,
                    "fat_grams": event.fat_grams,
                    "protein_grams": event.protein_grams,
                }
                for event in events
                if event.event_type == "meal"
            ],
        }

    def _meal_impact_risk(
        self,
        totals: dict[str, Any],
        glucose_context: dict[str, Any],
        recent_context: dict[str, Any],
        unmatched_items: list[str],
    ) -> dict[str, Any]:
        score = 0
        reasons = []

        carbs = _safe_float(totals.get("carbs_g"))
        fat = _safe_float(totals.get("fat_g"))
        protein = _safe_float(totals.get("protein_g"))
        latest_glucose = _safe_float(glucose_context.get("latest_value"))
        trend = str(glucose_context.get("trend") or "")

        if carbs is None:
            score += 2
            reasons.append("Carb estimate is incomplete.")
        elif carbs >= 90:
            score += 3
            reasons.append("Very high carbohydrate load.")
        elif carbs >= 60:
            score += 2
            reasons.append("High carbohydrate load.")
        elif carbs >= 30:
            score += 1
            reasons.append("Moderate carbohydrate load.")

        if fat is not None and fat >= 25:
            score += 2
            reasons.append("High fat may delay and prolong the glucose rise.")
        if protein is not None and protein >= 30:
            score += 1
            reasons.append("High protein may add a later glucose tail.")
        if latest_glucose is not None and latest_glucose > 180:
            score += 2
            reasons.append("Glucose is already above range.")
        if "rising" in trend:
            score += 1
            reasons.append("Recent glucose trend is rising.")
        if unmatched_items:
            score += 1
            reasons.append("Some requested items could not be matched.")
        if recent_context.get("recent_exercise"):
            reasons.append("Recent exercise may change insulin sensitivity.")
        if recent_context.get("recent_insulin"):
            reasons.append("Recent insulin may still be active.")

        if score >= 6:
            level = "high"
            recommendation = "Probably not a casual yes right now. Check live glucose, insulin-on-board, and your plan before eating."
        elif score >= 3:
            level = "moderate"
            recommendation = "Possible, but plan around the carb load and watch the delayed rise."
        else:
            level = "lower"
            recommendation = "Lower risk from the available data, but still check live glucose and use your usual plan."

        if fat is not None and fat >= 25 and carbs is not None and carbs >= 60:
            pattern = "early rise in 20-60 minutes, likely peak around 1-3 hours, and possible delayed second rise around 3-5 hours"
        elif carbs is not None and carbs >= 60:
            pattern = "early rise in 20-60 minutes with peak risk around 1-3 hours"
        elif fat is not None and fat >= 25:
            pattern = "smaller early rise but possible delayed rise around 3-5 hours"
        else:
            pattern = "modest rise, usually most visible in the first 1-2 hours"

        return {
            "risk_level": level,
            "risk_score": score,
            "expected_pattern": pattern,
            "recommendation": recommendation,
            "reasons": reasons,
        }

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
