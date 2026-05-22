---
name: "multi-provider-food-search"
description: "Implement multi-provider food search with priority ordering and fallback chain. Use when building a FoodService that queries local cache, local database, and online APIs in order of preference."
version: 2
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

When building a FoodService in T1D Companion that needs to:
- Search across multiple data sources in priority order
- Query local database before external APIs
- Return normalized results from all providers
- Cache external results locally

## Procedure
### 1. Define the search priority chain

```python
async def search_external_foods(
    self,
    session: AsyncSession,
    user_id: int,
    query: str,
    use_external: bool = True,
) -> List[Dict[str, Any]]:
    """Search for foods across local DB and external providers.
    
    Priority: local DB -> local OpenFoodFacts (Postgres) -> online OpenFoodFacts -> USDA
    External results are cached in the local Food table.
    """
    results = []
    
    # 1. Search local DB (highest priority)
    results.extend(await self._search_local_foods(user_id, query))
    
    if not use_external:
        return results
    
    # 2. Search local OpenFoodFacts (Postgres) - before online API
    local_off_results = await self._search_local_off(query, limit=5)
    for product in local_off_results:
        results.append(product)
        # Note: local OFF products are already in the lookup table,
        # no need to cache them again
    
    # 3. Search online OpenFoodFacts API as fallback if local OFF has no results
    # CRITICAL OPTIMIZATION: Only call online API when local OFF returns nothing
    # This prevents duplicate results and saves API calls
    if not local_off_results:
        off_results = await self._fetch_online_off(query)
        results.extend(self._cache_off_results(session, off_results, user_id))
    
    # 4. Search USDA (if API key configured)
    usda_results = await self._fetch_usda(query)
    results.extend(self._cache_usda_results(session, usda_results, user_id))
    
    if results:
        await session.commit()
    
    return results
```

### 2. Implement provider-specific search methods

Each provider should have its own method:

```python
async def _search_local_off(self, query: str, limit: int = 5) -> List[Dict]:
    """Query local Postgres openfoodfacts_products table.
    
    Uses trigram similarity for PostgreSQL, with ILIKE fallback for SQLite.
    Example implementation:
    
    stmt = (
        select(OpenFoodFactsProduct)
        .where(
            OpenFoodFactsProduct.product_name.isnot(None),
            OpenFoodFactsProduct.carbs_100g.isnot(None),
        )
        .order_by(
            func.similarity(OpenFoodFactsProduct.product_name, query).desc(),
            OpenFoodFactsProduct.nutriscore_score.asc().nullslast(),
        )
        .limit(limit)
    )
    """
    pass

async def _fetch_online_off(self, query: str) -> List[Dict]:
    """Call OpenFoodFacts API."""
    pass

async def _cache_off_results(self, session, results, user_id):
    """Convert to dicts and cache in local Food table."""
    for product in results:
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
    return results
```

### 3. Normalize result shape

All providers must return the same field set:

```python
NORMALIZED_FOOD_FIELDS = [
    "source",      # "local", "openfoodfacts_local", "openfoodfacts", "usda"
    "name",
    "brand",
    "barcode",     # or "fdc_id" for USDA
    "carbs_per_100g",
    "protein_per_100g",
    "fat_per_100g",
    "calories_per_100g",
    "serving_size",
]
```

### 4. Handle PostgreSQL trigram with SQLite fallback

```python
try:
    # PostgreSQL with pg_trgm extension
    stmt = select(Model).order_by(
        func.similarity(Model.name, query).desc()
    )
except Exception:
    # Fallback for SQLite or missing pg_trgm
    # Tokenize query and use ILIKE for each term
    terms = [t for t in query.split() if t]
    conditions = [Model.name.ilike(f"%{term}%") for term in terms]
    stmt = select(Model).where(or_(*conditions))
```
## Pitfalls

1. **Result deduplication**: Local OFF and online OFF may return the same product. Use barcode to deduplicate if needed.

2. **Source tracking**: Always mark `source="openfoodfacts_local"` vs `source="openfoodfacts"` so callers know the origin.

3. **Caching strategy**: Don't cache local OFF products again - they're already in the lookup table.

4. **API rate limits**: Online providers may fail; handle gracefully and continue with other providers.

5. **Transaction boundaries**: Commit cached results after all providers are attempted.

## Verification

```python
# Test priority ordering
async def test_priority_ordering(db_session, test_user):
    # Seed local OFF product
    local_off = OpenFoodFactsProduct(code="123", product_name="Local Chicken")
    db_session.add(local_off)
    await db_session.commit()
    
    # Mock online OFF response
    results = await service.search_external_foods(db_session, test_user.id, "chicken")
    
    # Should prefer local OFF over online
    assert any(r["source"] == "openfoodfacts_local" for r in results)
    assert not any(r["source"] == "openfoodfacts" for r in results)  # Shouldn't hit online
```