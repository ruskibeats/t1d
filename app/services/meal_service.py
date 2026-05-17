"""Meal tracker integration service.

Connects with open-source meal tracking platforms like OpenFoodFacts
to provide nutritional metrics and carb counts for meal logging.
Reference: https://world.openfoodfacts.org/
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContextEvent


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class OpenFoodFactsProduct(BaseModel):
    """OpenFoodFacts product representation."""
    
    code: str = Field(..., description="Product barcode")
    product_name: Optional[str] = Field(None, alias="product_name", description="Product name")
    product_name_en: Optional[str] = Field(None, description="Product name in English")
    brands: Optional[str] = Field(None, description="Brand names")
    categories: Optional[str] = Field(None, description="Category tags")
    
    # Nutritional information (per 100g)
    nutriments: Dict[str, Any] = Field(default_factory=dict)
    
    # Computed properties
    @property
    def carbohydrates(self) -> Optional[float]:
        """Carbohydrates in grams per 100g."""
        return self.nutriments.get("carbohydrates") or self.nutriments.get("carbohydrates_100g")
    
    @property
    def proteins(self) -> Optional[float]:
        """Proteins in grams per 100g."""
        return self.nutriments.get("proteins") or self.nutriments.get("proteins_100g")
    
    @property
    def fats(self) -> Optional[float]:
        """Fats in grams per 100g."""
        return self.nutriments.get("fat") or self.nutriments.get("fat_100g")
    
    @property
    def fiber(self) -> Optional[float]:
        """Fiber in grams per 100g."""
        return self.nutriments.get("fiber") or self.nutriments.get("fiber_100g")
    
    @property
    def sugars(self) -> Optional[float]:
        """Sugars in grams per 100g."""
        return self.nutriments.get("sugars") or self.nutriments.get("sugars_100g")
    
    @property
    def energy_kcal(self) -> Optional[float]:
        """Energy in kilocalories per 100g."""
        # Prefer kcal, fall back to kJ conversion
        kcal = self.nutriments.get("energy-kcal") or self.nutriments.get("energy_kcal")
        if kcal:
            return kcal
        kj = self.nutriments.get("energy") or self.nutriments.get("energy_100g")
        if kj:
            return round(kj / 4.184, 1)
        return None
    
    @property
    def glycemic_index(self) -> Optional[int]:
        """Estimated glycemic index (0-100)."""
        # This would typically come from a separate database
        # For now, estimate based on food category and sugar content
        categories_lower = (self.categories or "").lower()
        sugars = self.sugars or 0
        
        if "vegetable" in categories_lower or "salad" in categories_lower:
            return 15
        if "meat" in categories_lower or "fish" in categories_lower or "egg" in categories_lower:
            return 0
        if "cheese" in categories_lower or "dairy" in categories_lower:
            return 30
        if "nut" in categories_lower or "seed" in categories_lower:
            return 15
        if "bread" in categories_lower or "pasta" in categories_lower:
            return 50 if "whole" in categories_lower else 70
        if "rice" in categories_lower:
            return 50 if "brown" in categories_lower else 73
        if "potato" in categories_lower:
            return 85 if "fried" in categories_lower else 70
        if "fruit" in categories_lower:
            if sugars > 10:
                return 60
            return 40
        if "sugar" in categories_lower or "sweet" in categories_lower or "candy" in categories_lower:
            return 85
        if "cereal" in categories_lower:
            return 65
        
        # Default estimate based on sugar content
        if sugars > 20:
            return 70
        if sugars > 10:
            return 55
        return 45


class MealSearchResult(BaseModel):
    """Result from meal/nutrition database search."""
    
    products: List[OpenFoodFactsProduct] = Field(default_factory=list)
    total_count: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=20)


class MealNutritionSummary(BaseModel):
    """Nutritional summary for a logged meal."""
    
    total_carbs: float = Field(..., description="Total carbohydrates (g)")
    total_proteins: float = Field(..., description="Total proteins (g)")
    total_fats: float = Field(..., description="Total fats (g)")
    total_fiber: float = Field(..., description="Total fiber (g)")
    total_sugars: float = Field(..., description="Total sugars (g)")
    total_calories: float = Field(..., description="Total calories (kcal)")
    estimated_glycemic_index: float = Field(..., description="Weighted average GI")
    insulin_carb_ratio: Optional[float] = Field(None, description="Insulin per carb unit (user-specific)")
    estimated_insulin_needed: Optional[float] = Field(None, description="Estimated insulin units needed")


class MealLogItem(BaseModel):
    """Item in a meal log."""
    
    product: Optional[OpenFoodFactsProduct] = None
    food_name: str = Field(..., description="Name of food item")
    serving_size: float = Field(..., description="Serving size in grams")
    servings: float = Field(default=1.0, description="Number of servings")
    carbs: Optional[float] = Field(None, description="Carbohydrates (g)")
    proteins: Optional[float] = Field(None, description="Proteins (g)")
    fats: Optional[float] = Field(None, description="Fats (g)")

    @field_validator('serving_size', 'servings')
    @classmethod
    def positive_values(cls, v):
        if v <= 0:
            raise ValueError("must be positive")
        return v


class MealLogCreate(BaseModel):
    """Request model for logging a meal."""
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meal_items: List[MealLogItem] = Field(..., min_length=1)
    notes: Optional[str] = Field(None, description="Additional notes")
    pre_bolus_taken: bool = Field(default=False, description="Was pre-bolus taken?")
    pre_bolus_minutes: Optional[int] = Field(None, description="Minutes before eating")


# ---------------------------------------------------------------------------
# Service Errors
# ---------------------------------------------------------------------------

class MealServiceError(Exception):
    """Raised when meal service operations fail."""
    pass


# ---------------------------------------------------------------------------
# Main Service
# ---------------------------------------------------------------------------

class MealService:
    """Service for meal tracking and nutritional analysis.
    
    Integrates with OpenFoodFacts and similar open-source food databases
to provide comprehensive nutritional information for diabetes management.
    """
    
    def __init__(
        self,
        openfoodfacts_url: str = "https://world.openfoodfacts.org",
        timeout: float = 30.0,
    ):
        """Initialize meal service.
        
        Args:
            openfoodfacts_url: Base URL for OpenFoodFacts API
            timeout: HTTP request timeout in seconds
        """
        self.base_url = openfoodfacts_url.rstrip("/")
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.MealService")
    
    # -------------------------------------------------------------------
    # OpenFoodFacts Integration
    # -------------------------------------------------------------------
    
    async def search_product(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> MealSearchResult:
        """Search for food products in OpenFoodFacts.
        
        Args:
            query: Search query (product name, brand, etc.)
            page: Page number for pagination
            page_size: Number of results per page
            
        Returns:
            Search results with matching products
            
        Raises:
            MealServiceError: If search fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/cgi/search.pl",
                    params={
                        "search_terms": query,
                        "search_simple": 0,
                        "json": 1,
                        "page": page,
                        "page_size": page_size,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                products_raw = data.get("products", [])
                products = []
                
                for product_raw in products_raw:
                    try:
                        # Normalize nutriments keys
                        nutriments = product_raw.get("nutriments", {})
                        # Handle both flat and nested nutritional data
                        if not isinstance(nutriments, dict):
                            nutriments = {}
                        
                        product = OpenFoodFactsProduct(
                            code=product_raw.get("code", ""),
                            product_name=product_raw.get("product_name"),
                            product_name_en=product_raw.get("product_name_en"),
                            brands=product_raw.get("brands"),
                            categories=product_raw.get("categories"),
                            nutriments=nutriments,
                        )
                        products.append(product)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse product: {e}")
                        continue
                
                total_count = data.get("count", len(products))
                
                return MealSearchResult(
                    products=products,
                    total_count=total_count,
                    page=page,
                    page_size=page_size,
                )
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"OpenFoodFacts search failed: {e}")
                raise MealServiceError(
                    f"Search failed: {e.response.text}"
                ) from e
            except Exception as e:
                self.logger.error(f"OpenFoodFacts search error: {e}")
                raise MealServiceError(f"Search failed: {str(e)}") from e
    
    async def get_product_by_barcode(
        self,
        barcode: str,
    ) -> Optional[OpenFoodFactsProduct]:
        """Retrieve product details by barcode.
        
        Args:
            barcode: Product barcode (EAN/UPC)
            
        Returns:
            Product details or None if not found
            
        Raises:
            MealServiceError: If lookup fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v2/product/{barcode}",
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") != 1:
                    return None
                
                product_raw = data.get("product", {})
                nutriments = product_raw.get("nutriments", {})
                
                if not isinstance(nutriments, dict):
                    nutriments = {}
                
                return OpenFoodFactsProduct(
                    code=product_raw.get("code", barcode),
                    product_name=product_raw.get("product_name"),
                    product_name_en=product_raw.get("product_name_en"),
                    brands=product_raw.get("brands"),
                    categories=product_raw.get("categories"),
                    nutriments=nutriments,
                )
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                self.logger.error(f"Barcode lookup failed: {e}")
                raise MealServiceError(
                    f"Lookup failed: {e.response.text}"
                ) from e
            except Exception as e:
                self.logger.error(f"Barcode lookup error: {e}")
                raise MealServiceError(f"Lookup failed: {str(e)}") from e
    
    # -------------------------------------------------------------------
    # Meal Calculation
    # -------------------------------------------------------------------
    
    def calculate_nutrition_summary(
        self,
        meal_items: List[MealLogItem],
        user_insulin_ratio: Optional[float] = None,
    ) -> MealNutritionSummary:
        """Calculate total nutritional values for a meal.
        
        Args:
            meal_items: List of meal items with serving sizes
            user_insulin_ratio: Insulin-to-carb ratio (units per gram)
            
        Returns:
            Complete nutritional summary
        """
        total_carbs = 0.0
        total_proteins = 0.0
        total_fats = 0.0
        total_fiber = 0.0
        total_sugars = 0.0
        total_calories = 0.0
        
        weighted_gi_total = 0.0
        total_carbs_for_gi = 0.0
        
        for item in meal_items:
            # Scale factor based on serving size
            scale = item.serving_size * item.servings
            
            if item.product:
                # Use product data
                carbs = (item.product.carbohydrates or 0) * scale / 100.0
                proteins = (item.product.proteins or 0) * scale / 100.0
                fats = (item.product.fats or 0) * scale / 100.0
                fiber = (item.product.fiber or 0) * scale / 100.0
                sugars = (item.product.sugars or 0) * scale / 100.0
                calories = (item.product.energy_kcal or 0) * scale / 100.0
                gi = item.product.glycemic_index or 45
            else:
                # Use manually entered values
                carbs = item.carbs or 0
                proteins = item.proteins or 0
                fats = item.fats or 0
                fiber = 0  # Unknown without product data
                sugars = 0  # Unknown without product data
                calories = carbs * 4 + proteins * 4 + fats * 9  # Atwater factors
                gi = 45  # Default estimate
            
            total_carbs += carbs
            total_proteins += proteins
            total_fats += fats
            total_fiber += fiber
            total_sugars += sugars
            total_calories += calories
            
            # Weighted GI calculation (only carbs contribute)
            if carbs > 0:
                weighted_gi_total += gi * carbs
                total_carbs_for_gi += carbs
        
        # Calculate weighted average GI
        if total_carbs_for_gi > 0:
            estimated_gi = weighted_gi_total / total_carbs_for_gi
        else:
            estimated_gi = 45.0
        
        # Estimate insulin needed if ratio provided
        insulin_needed = None
        if user_insulin_ratio and user_insulin_ratio > 0:
            insulin_needed = round(total_carbs / user_insulin_ratio, 1)
        
        return MealNutritionSummary(
            total_carbs=round(total_carbs, 1),
            total_proteins=round(total_proteins, 1),
            total_fats=round(total_fats, 1),
            total_fiber=round(total_fiber, 1),
            total_sugars=round(total_sugars, 1),
            total_calories=round(total_calories),
            estimated_glycemic_index=round(estimated_gi, 1),
            insulin_carb_ratio=user_insulin_ratio,
            estimated_insulin_needed=insulin_needed,
        )
    
    # -------------------------------------------------------------------
    # Data Ingestion
    # -------------------------------------------------------------------
    
    async def log_meal_event(
        self,
        session: AsyncSession,
        user_id: int,
        meal_data: MealLogCreate,
        insulin_ratio: Optional[float] = None,
    ) -> ContextEvent:
        """Log a meal event with nutritional analysis.
        
        Creates a ContextEvent with meal-specific nutritional data.
        
        Args:
            session: Database session
            user_id: ID of the user logging the meal
            meal_data: Meal data including items and metadata
            insulin_ratio: User's insulin-to-carb ratio
            
        Returns:
            Created context event with meal data
            
        Raises:
            MealServiceError: If logging fails
        """
        from sqlalchemy import select
        
        try:
            # Calculate nutritional summary
            nutrition = self.calculate_nutrition_summary(
                meal_data.meal_items,
                insulin_ratio,
            )
            
            # Create context event with meal and nutritional data
            event = ContextEvent(
                user_id=user_id,
                event_type="meal",
                event_subtype="logged",
                timestamp=meal_data.timestamp,
                duration=0,  # Meals are point-in-time events
                notes=meal_data.notes or "",
                carbs_grams=nutrition.total_carbs,
                protein_grams=nutrition.total_proteins,
                fat_grams=nutrition.total_fats,
                calories=int(nutrition.total_calories),
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            
            self.logger.info(
                f"Meal logged for user {user_id}: "
                f"{nutrition.total_carbs}g carbs, "
                f"GI={nutrition.estimated_glycemic_index}"
            )
            
            return event
            
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Failed to log meal: {e}")
            raise MealServiceError(f"Meal logging failed: {str(e)}") from e
    
    async def get_user_meal_history(
        self,
        session: AsyncSession,
        user_id: int,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get user's meal history with nutritional analysis.
        
        Args:
            session: Database session
            user_id: ID of the user
            days: Number of days to look back
            
        Returns:
            List of meal events with nutritional data
        """
        from sqlalchemy import select
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        result = await session.execute(
            select(ContextEvent)
            .where(
                ContextEvent.user_id == user_id,
                ContextEvent.event_type == "meal",
                ContextEvent.timestamp >= cutoff_date,
            )
            .order_by(ContextEvent.timestamp.desc())
        )
        
        meals = []
        for event in result.scalars().all():
            time_diff = (datetime.now(timezone.utc) - event.timestamp).total_seconds() / 3600
            meals.append({
                "event_id": event.id,
                "timestamp": event.timestamp,
                "hours_ago": round(time_diff, 1),
                "notes": event.notes,
                "carbohydrates": event.carbs_grams,
                "proteins": event.protein_grams,
                "fats": event.fat_grams,
                "calories": event.calories,
            })
        
        return meals


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def estimate_carbs_from_description(food_desc: str) -> Optional[float]:
    """Rough carb estimation from meal description (fallback)."""
    food_lower = food_desc.lower()
    
    # Very rough estimates
    if "pizza" in food_lower:
        return 40  # per slice
    if "pasta" in food_lower or "spaghetti" in food_lower:
        return 45  # per cup
    if "rice" in food_lower:
        return 45  # per cup
    if "bread" in food_lower:
        return 15  # per slice
    if "sandwich" in food_lower:
        return 30
    if "salad" in food_lower:
        return 10
    if "fruit" in food_lower or "apple" in food_lower or "banana" in food_lower:
        return 25
    if "chicken" in food_lower or "beef" in food_lower or "fish" in food_lower:
        return 0  # Protein only
    if "vegetable" in food_lower:
        return 5
    if "dessert" in food_lower or "cake" in food_lower or "cookie" in food_lower:
        return 50
    if "cereal" in food_lower:
        return 30
    
    return None


def calculate_correction_units(
    current_bg: float,
    target_bg: float,
    correction_factor: float,
) -> float:
    """Calculate insulin correction units for high blood glucose.
    
    Args:
        current_bg: Current blood glucose (mg/dL)
        target_bg: Target blood glucose (mg/dL)
        correction_factor: mg/dL per unit of insulin
        
    Returns:
        Insulin units needed for correction
    """
    if current_bg <= target_bg:
        return 0.0
    
    excess = current_bg - target_bg
    units = excess / correction_factor
    return round(units, 1)
