---
name: "meal-impact-forecast-with-local-off"
description: "Build meal impact forecasts combining local nutrition lookup with personal glucose patterns"
version: 2
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

Implementing a meal impact endpoint that:
- Looks up nutrition data from local Open Food Facts database
- Combines with user's recent glucose history
- Provides rules-based forecasts with personalized insights
- Works with PostgreSQL trigram similarity for fuzzy matching

## Procedure
### 1. Add Meal Impact Models to Service Layer
```python
# app/food/service.py
async def estimate_meal_impact(
    self,
    user_id: int,
    items: List[str],
    eaten_at: Optional[datetime] = None,
) -> MealImpactResponse:
```

### 2. Implement Local OFF Lookup with Similarity Ranking
- Use `func.similarity()` for PostgreSQL trigram matching
- Fall back to ILIKE for SQLite compatibility
- Return products sorted by similarity score + nutriscore
- Filter to products with nutrition data (`carbs_100g.isnot(None)`)

### 3. Fetch Historical Context
- Recent glucose readings (last 3 hours before meal time)
- Recent meal/insulin/exercise events (last 4 hours)
- Calculate trend from readings (rising/falling/fast rates)

### 4. Build Rules-Based Risk Assessment
- Carb load thresholds: ≥90g (very high), 60-89g (high), 30-59g (moderate), <30g (low)
- Fat contribution: ≥25g increases risk and may cause delayed glucose rise
- Protein contribution: ≥30g may add a later glucose tail
- Personal pattern adjustment: query health_metrics for hour-of-day baselines

### 5. Serving Size Heuristics
- Parse serving size strings (e.g., "100 g", "1 cup (240ml)") to extract grams
- For restaurant/fast-food items like "large fries", use conservative estimates
  (150g for large, 115g for medium, 75g for small) to avoid undercounting

### 6. Return Safety-Compliant Response
Include explicit safety note:
```python
"safety_note": (
    "This is educational decision support, not dosing advice. "
    "Use your prescribed insulin plan and check live CGM/fingerstick data."
)
```
## Pitfalls

- **Database parity**: PostgreSQL trigram similarity doesn't exist in SQLite - tests use ILIKE fallback
- **Duplicate prevention**: `hash(item)` for deduplication can cause collisions; use proper unique constraints
- **Time windows**: Context event fetching needs careful time bounds (events within meal impact window)
- **Carbohydrate estimation**: Some foods have `sugars` but NULL `carbs_100g` - handle gracefully

## Verification

1. Run `pytest tests/test_food_providers.py -v` - all tests pass
2. Query `openfoodfacts_products` directly: `SELECT * FROM openfoodfacts_products WHERE carbs_100g > 0 LIMIT 5`
3. Check Postgres trigram extension: `SELECT * FROM pg_extension WHERE extname = 'pg_trgm'`
4. Verify meal endpoint: `curl -X POST /food/meal-impact -d '{"items": ["stella lager"]}'`