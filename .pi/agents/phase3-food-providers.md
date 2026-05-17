---
name: phase3-food-providers
description: Implements the OpenFoodFacts and USDA FoodData Central API clients for the T1D Companion food search feature. Use when implementing Phase 3 food database integration.
model: openai/gpt-oss-120b:free
context: fork
---

# Phase 3: Food Database Integration

## Task

Implement two external food database API clients and wire them into the food search service:
1. **OpenFoodFacts** — free, open-source food database with barcode search
2. **USDA FoodData Central** — US government nutrition database

The `FoodService.search()` method should query the local DB first, then fall back to external providers, caching results locally.

## Files to Modify/Create

- `app/food/providers/openfoodfacts.py` — implement OpenFoodFacts API client
- `app/food/providers/usda.py` — implement USDA API client
- `app/food/service.py` — wire providers into `FoodService.search()`

## Part 1: OpenFoodFacts Provider

`app/food/providers/openfoodfacts.py` — already exists as a stub. Implement:

```python
"""OpenFoodFacts API client.

Free, open-source food database.
API docs: https://world.openfoodfacts.org/data
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

OPENFOODFACTS_BASE_URL = "https://world.openfoodfacts.org"


class OpenFoodFactsProduct(BaseModel):
    """Parsed OpenFoodFacts product."""
    
    name: str = Field(..., description="Product name")
    brand: str | None = Field(None, description="Brand name")
    barcode: str | None = Field(None, description="Barcode/EAN")
    carbs_per_100g: float | None = Field(None, description="Carbohydrates per 100g")
    protein_per_100g: float | None = Field(None, description="Protein per 100g")
    fat_per_100g: float | None = Field(None, description="Fat per 100g")
    calories_per_100g: float | None = Field(None, description="Calories per 100g (kcal)")
    serving_size: str | None = Field(None, description="Serving size string")
    categories: list[str] = Field(default_factory=list)


class OpenFoodFactsClient:
    """Client for OpenFoodFacts API."""
    
    def __init__(self, base_url: str = OPENFOODFACTS_BASE_URL):
        self.base_url = base_url
    
    async def search_by_name(
        self,
        query: str,
        page_size: int = 10,
    ) -> List[OpenFoodFactsProduct]:
        """Search for products by name.
        
        Args:
            query: Search term (e.g., "pasta", "chicken breast")
            page_size: Number of results to return
            
        Returns:
            List of parsed products
        """
        url = f"{self.base_url}/cgi/search.pl"
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": page_size,
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            products = []
            for item in data.get("products", []):
                try:
                    nutriments = item.get("nutriments", {})
                    product = OpenFoodFactsProduct(
                        name=item.get("product_name", item.get("product_name_en", "Unknown")),
                        brand=item.get("brands", None),
                        barcode=item.get("code", None),
                        carbs_per_100g=nutriments.get("carbohydrates_100g"),
                        protein_per_100g=nutriments.get("proteins_100g"),
                        fat_per_100g=nutriments.get("fat_100g"),
                        calories_per_100g=nutriments.get("energy-kcal_100g"),
                        serving_size=item.get("serving_size", None),
                        categories=item.get("categories_tags", [])[:5],
                    )
                    # Only include products with at least a name and some nutrition data
                    if product.name and product.name != "Unknown":
                        products.append(product)
                except Exception as e:
                    logger.debug(f"Skipping malformed OpenFoodFacts product: {e}")
                    continue
            
            return products
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenFoodFacts search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"OpenFoodFacts error: {e}")
            return []
    
    async def search_by_barcode(self, barcode: str) -> OpenFoodFactsProduct | None:
        """Search for a product by barcode.
        
        Args:
            barcode: EAN/UPC barcode string
            
        Returns:
            Product if found, None otherwise
        """
        url = f"{self.base_url}/api/v0/product/{barcode}.json"
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("status") != 1:
                return None
            
            product_data = data["product"]
            nutriments = product_data.get("nutriments", {})
            
            return OpenFoodFactsProduct(
                name=product_data.get("product_name", product_data.get("product_name_en", "Unknown")),
                brand=product_data.get("brands", None),
                barcode=barcode,
                carbs_per_100g=nutriments.get("carbohydrates_100g"),
                protein_per_100g=nutriments.get("proteins_100g"),
                fat_per_100g=nutriments.get("fat_100g"),
                calories_per_100g=nutriments.get("energy-kcal_100g"),
                serving_size=product_data.get("serving_size", None),
                categories=product_data.get("categories_tags", [])[:5],
            )
            
        except Exception as e:
            logger.error(f"OpenFoodFacts barcode search failed: {e}")
            return None
```

## Part 2: USDA FoodData Central Provider

`app/food/providers/usda.py` — already exists as a stub. Implement:

```python
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
```

### Add USDA API Key to Settings

In `app/config.py`, add to the `Settings` class:

```python
# USDA FoodData Central
usda_api_key: str | None = os.getenv("USDA_API_KEY")
```

## Part 3: Wire Into FoodService

In `app/food/service.py`, update the `FoodService.search()` method:

```python
async def search_foods(
    self,
    session: AsyncSession,
    user_id: int,
    query: str,
    use_external: bool = True,
) -> List[Dict[str, Any]]:
    """Search for foods across local DB and external providers.
    
    Priority: local DB → OpenFoodFacts → USDA
    External results are cached in the local Food table.
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
            "carbs_per_100g": food.carbs_per_100g,
            "protein_per_100g": food.protein_per_100g,
            "fat_per_100g": food.fat_per_100g,
            "calories_per_100g": food.calories_per_100g,
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
            brand=product.brand,
            barcode=product.barcode,
            carbs_per_100g=product.carbs_per_100g,
            protein_per_100g=product.protein_per_100g,
            fat_per_100g=product.fat_per_100g,
            calories_per_100g=product.calories_per_100g,
            serving_size=product.serving_size,
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
```

## Critical Rules

1. **Modify only:** `app/food/providers/openfoodfacts.py`, `app/food/providers/usda.py`, `app/food/service.py`, `app/config.py`
2. **Handle API failures gracefully** — if OpenFoodFacts or USDA is down, return empty results, don't crash
3. **Cache external results** — store in local Food table to avoid repeated API calls
4. **Respect rate limits** — OpenFoodFacts has no auth but be polite; USDA has rate limits
5. **Don't require USDA API key** — the system should work without it (OpenFoodFacts is free, no key needed)
6. **Normalize nutrition data** — all providers return per-100g values

## Verification

After writing, verify:
- [ ] `OpenFoodFactsClient.search_by_name()` returns parsed products
- [ ] `OpenFoodFactsClient.search_by_barcode()` returns a single product
- [ ] `USDAClient.search_by_name()` returns parsed food items
- [ ] `FoodService.search()` queries local DB first, then external providers
- [ ] External results are cached in the Food table
- [ ] No import errors: `python -c "from app.food.providers.openfoodfacts import OpenFoodFactsClient; print('OK')"`
- [ ] No import errors: `python -c "from app.food.providers.usda import USDAClient; print('OK')"`
- [ ] No import errors: `python -c "from app.food.service import FoodService; print('OK')"`

## Output

Write your implementation notes to: `PHASE3_W8_FOOD_PROVIDERS.md`
