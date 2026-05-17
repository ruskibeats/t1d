---
name: phase3-food-providers-v2
description: Implements OpenFoodFacts and USDA food API clients. Use write() tool for ALL files. Do NOT output code in response text.
model: poolside/laguna-m.1:free
context: fork
---

# Phase 3: Food Providers (v2)

## Task
Implement OpenFoodFacts and USDA FoodData Central API clients and wire into FoodService.

## CRITICAL RULES
1. Use the `write()` tool to create files. NEVER output code in response text.
2. First read existing files to understand current stubs and patterns.
3. Write each file in ONE write() call.

## Steps
1. Read existing files:
   - `app/food/providers/openfoodfacts.py`
   - `app/food/providers/usda.py`
   - `app/food/service.py`
   - `app/food/models.py`
   - `app/config.py`

2. Use write() to overwrite `app/food/providers/openfoodfacts.py`:
   - OpenFoodFactsClient class with search_by_name() and search_by_barcode()
   - Uses httpx.AsyncClient, base URL: https://world.openfoodfacts.org
   - Returns list of dicts with: name, brand, barcode, carbs_per_100g, protein_per_100g, fat_per_100g, calories_per_100g, serving_size
   - Handle errors gracefully (return [] on failure)

3. Use write() to overwrite `app/food/providers/usda.py`:
   - USDAClient class with search_by_name()
   - Uses httpx.AsyncClient, base URL: https://api.nal.usda.gov/fdc/v1
   - API key from settings.usda_api_key (add to config.py if missing)
   - Returns list of dicts with same fields as OpenFoodFacts
   - Handle errors gracefully (return [] on failure or no API key)

4. Use write() to add `usda_api_key: str | None = os.getenv("USDA_API_KEY")` to Settings in `app/config.py`

5. Use write() to update `app/food/service.py`:
   - Import both providers
   - In search method: query local DB first, then OpenFoodFacts, then USDA
   - Cache external results in Food table

6. Run: `cd /root/t1d && python -c "from app.food.providers.openfoodfacts import OpenFoodFactsClient; print('off OK')"`
7. Run: `cd /root/t1d && python -c "from app.food.providers.usda import USDAClient; print('usda OK')"`
8. Run: `cd /root/t1d && python -c "from app.food.service import FoodService; print('food OK')"`

9. Use write() to save notes to `PHASE3_W8_FOOD_PROVIDERS.md`

## Output
Write implementation notes to: `PHASE3_W8_FOOD_PROVIDERS.md`
