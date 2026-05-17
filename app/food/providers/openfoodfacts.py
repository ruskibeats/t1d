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