"""OpenFoodFacts food database integration.

Provides search capabilities against the OpenFoodFacts public API.
"""

from typing import Optional

import httpx
from pydantic import TypeAdapter

from app.food.schemas import FoodCreate, FoodResponse


class OpenFoodFactsProvider:
    """Client for the OpenFoodFacts public API.

    Provides search by name and barcode using the free, open database.
    """

    SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
    PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def search_by_name(self, query: str, limit: int = 10) -> list[FoodCreate]:
        """Search foods by name.

        Args:
            query: Search term (e.g., "banana", "chicken breast").
            limit: Maximum results to return.

        Returns:
            List of FoodCreate objects parsed from OpenFoodFacts results.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.SEARCH_URL,
                params={
                    "search_terms": query,
                    "page_size": limit,
                    "json": "true",
                },
            )
            response.raise_for_status()
            data = response.json()

        products = data.get("products", [])
        results = []
        for product in products:
            food = self._parse_product(product)
            if food is not None:
                results.append(food)
        return results

    async def search_by_barcode(self, barcode: str) -> Optional[FoodCreate]:
        """Search a single food by barcode.

        Args:
            barcode: Product barcode (EAN-13 or similar).

        Returns:
            FoodCreate if found, None otherwise.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.PRODUCT_URL.format(barcode=barcode),
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status", 0) != 1:
            return None

        product = data.get("product", {})
        return self._parse_product(product)

    def _parse_product(self, product: dict) -> Optional[FoodCreate]:
        """Parse a single OpenFoodFacts product dict into FoodCreate."""
        name = product.get("product_name") or product.get("product_name_en")
        if not name:
            return None

        nutriments = product.get("nutriments", {}) or {}
        return FoodCreate(
            name=str(name)[:255],
            brand_name=product.get("brands"),
            barcode=str(product.get("code", "")),
            serving_size=nutriments.get("serving_quantity"),
            serving_unit=nutriments.get("serving_quantity_unit", "g"),
            calories=nutriments.get("energy-kcal_100g") or nutriments.get("energy-kcal"),
            protein=nutriments.get("proteins_100g") or nutriments.get("proteins"),
            carbs=nutriments.get("carbohydrates_100g") or nutriments.get("carbohydrates"),
            fat=nutriments.get("fat_100g") or nutriments.get("fat"),
            fiber=nutriments.get("fiber_100g") or nutriments.get("fiber"),
            sugars=nutriments.get("sugars_100g") or nutriments.get("sugars"),
            sodium=nutriments.get("sodium_100g") or nutriments.get("sodium"),
            source="openfoodfacts",
        )
