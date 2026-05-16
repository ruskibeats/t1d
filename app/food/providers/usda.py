"""USDA FoodData Central food database integration.

Provides search capabilities against the USDA FoodData Central API.
"""

from typing import Optional

import httpx

from app.food.schemas import FoodCreate


class USDAProvider:
    """Client for the USDA FoodData Central API.

    Searches the USDA food database by name. Requires an API key from
    https://fdc.nal.usda.gov/api-key-signup.html
    The "DEMO_KEY" is rate-limited to 1 request/second.
    """

    SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

    # Mapping of USDA nutrient names to our field names
    NUTRIENT_MAP: dict[str, str] = {
        "Carbohydrates, by difference": "carbs",
        "Carbohydrate, by difference": "carbs",
        "Protein": "protein",
        "Total lipid (fat)": "fat",
        "Total fat": "fat",
        "Energy": "calories",
        "Fiber, total dietary": "fiber",
        "Fiber": "fiber",
        "Sugars, total including NLEA": "sugars",
        "Total Sugars": "sugars",
        "Sodium, Na": "sodium",
    }

    def __init__(self, api_key: str = "DEMO_KEY", timeout: float = 15.0):
        self.api_key = api_key
        self.timeout = timeout

    async def search_usda(self, query: str, page_size: int = 10) -> list[FoodCreate]:
        """Search USDA food database by name.

        Args:
            query: Search term.
            page_size: Maximum results per page.

        Returns:
            List of FoodCreate objects.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.SEARCH_URL,
                params={
                    "query": query,
                    "api_key": self.api_key,
                    "pageSize": page_size,
                    "dataType": ["Foundation", "SR Legacy", "Branded"],
                },
            )
            response.raise_for_status()
            data = response.json()

        foods = data.get("foods", [])
        results = []
        for food in foods:
            parsed = self._parse_food(food)
            if parsed is not None:
                results.append(parsed)
        return results

    def _parse_food(self, food: dict) -> Optional[FoodCreate]:
        """Parse a single USDA food item into FoodCreate."""
        description = food.get("description")
        if not description:
            return None

        nutrients: dict[str, float] = {}
        for nutrient in food.get("foodNutrients", []):
            name = nutrient.get("nutrientName") or nutrient.get("name", "")
            value = nutrient.get("value")
            for usda_name, our_field in self.NUTRIENT_MAP.items():
                if usda_name.lower() in name.lower():
                    if value is not None:
                        nutrients[our_field] = float(value)
                    break

        return FoodCreate(
            name=str(description)[:255],
            brand_name=food.get("brandName") or food.get("brandOwner"),
            barcode=str(food.get("fdcId", "")),
            serving_size=100.0,
            serving_unit="g",
            calories=nutrients.get("calories"),
            protein=nutrients.get("protein"),
            carbs=nutrients.get("carbs"),
            fat=nutrients.get("fat"),
            fiber=nutrients.get("fiber"),
            sugars=nutrients.get("sugars"),
            sodium=nutrients.get("sodium"),
            source="usda",
        )
