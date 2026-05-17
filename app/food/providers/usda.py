"""USDA FoodData Central API client.

US government nutrition database.
API docs: https://fdc.nal.usda.gov/api-guide.html
Requires free API key from: https://fdc.nal.usda.gov/api-key-signup.html
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"


class USDAFoodItem(BaseModel):
    """Parsed USDA food item."""
    
    name: str = Field(..., description="Food description")
    brand: str | None = Field(None, description="Brand owner")
    fdc_id: int = Field(..., description="USDA FDC ID")
    carbs_per_100g: float | None = Field(None, description="Carbohydrates per 100g")
    protein_per_100g: float | None = Field(None, description="Protein per 100g")
    fat_per_100g: float | None = Field(None, description="Fat per 100g")
    calories_per_100g: float | None = Field(None, description="Calories per 100g (kcal)")
    serving_size: float | None = Field(None, description="Serving size in grams")
    serving_unit: str | None = Field(None, description="Serving unit")
    food_category: str | None = Field(None, description="Food category")


class USDAClient:
    """Client for USDA FoodData Central API."""
    
    def __init__(self, api_key: str | None = None):
        from app.config import get_settings
        self.api_key = api_key or get_settings().usda_api_key
    
    async def search_by_name(
        self,
        query: str,
        page_size: int = 10,
    ) -> List[USDAFoodItem]:
        """Search for foods by name.
        
        Args:
            query: Search term (e.g., "chicken breast", "brown rice")
            page_size: Number of results to return
            
        Returns:
            List of parsed food items
        """
        if not self.api_key:
            logger.warning("USDA API key not configured")
            return []
        
        url = f"{USDA_BASE_URL}/foods/search"
        params = {
            "query": query,
            "pageSize": page_size,
            "api_key": self.api_key,
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            foods = data.get("foods", [])
            results = []
            
            for item in foods:
                try:
                    # Extract nutrients
                    nutrients = {n["nutrientName"]: n["value"] for n in item.get("foodNutrients", [])}
                    
                    food = USDAFoodItem(
                        name=item.get("description", "Unknown"),
                        brand=item.get("brandOwner", None),
                        fdc_id=item.get("fdcId", 0),
                        carbs_per_100g=nutrients.get("Carbohydrate, by difference"),
                        protein_per_100g=nutrients.get("Protein"),
                        fat_per_100g=nutrients.get("Total lipid (fat)"),
                        calories_per_100g=nutrients.get("Energy"),
                        serving_size=item.get("servingSize"),
                        serving_unit=item.get("servingSizeUnit"),
                        food_category=item.get("foodCategory", None),
                    )
                    results.append(food)
                except Exception as e:
                    logger.debug(f"Skipping malformed USDA food item: {e}")
                    continue
            
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(f"USDA search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"USDA error: {e}")
            return []