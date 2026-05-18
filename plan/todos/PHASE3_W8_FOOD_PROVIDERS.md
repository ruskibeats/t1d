# PHASE3 W8: Food Providers Implementation

## Summary
Implemented OpenFoodFacts and USDA FoodData Central API clients for the T1D Companion food search feature.

## Files Modified

### 1. `app/food/providers/openfoodfacts.py`
- Implemented `OpenFoodFactsProduct` Pydantic model with fields:
  - `name`, `brand`, `barcode`
  - `carbs_per_100g`, `protein_per_100g`, `fat_per_100g`, `calories_per_100g`
  - `serving_size`, `categories`

- Implemented `OpenFoodFactsClient` class with methods:
  - `search_by_name(query, page_size=10)` - Search products by name
  - `search_by_barcode(barcode)` - Search single product by barcode

### 2. `app/food/providers/usda.py`
- Implemented `USDAFoodItem` Pydantic model with fields:
  - `name`, `brand`, `fdc_id`
  - `carbs_per_100g`, `protein_per_100g`, `fat_per_100g`, `calories_per_100g`
  - `serving_size`, `serving_unit`, `food_category`

- Implemented `USDAClient` class with method:
  - `search_by_name(query, page_size=10)` - Search foods by name

### 3. `app/config.py`
- Added `usda_api_key: str | None = os.getenv("USDA_API_KEY")` to Settings class

### 4. `app/food/service.py`
- Added new `search_foods()` method that:
  - Queries local DB first
  - Falls back to OpenFoodFacts
  - Falls back to USDA (if API key configured)
  - Caches external results in local Food table
  - Returns `List[Dict[str, Any]]` with nutrition data per 100g

### 5. `app/food/providers/__init__.py`
- Updated exports to include new classes: `OpenFoodFactsClient`, `OpenFoodFactsProduct`, `USDAClient`, `USDAFoodItem`

## Verification Results
- ✅ `OpenFoodFactsClient` imports successfully
- ✅ `USDAClient` imports successfully
- ✅ `FoodService` imports successfully
- ✅ All provider classes are properly exported

## Notes
- OpenFoodFacts requires no API key (free, open-source)
- USDA requires free API key from https://fdc.nal.usda.gov/api-key-signup.html
- Both clients handle API failures gracefully (return empty lists, not crashes)
- Nutrition data normalized to per-100g values across all providers