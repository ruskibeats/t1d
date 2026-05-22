---
name: "sqlalchemy-trigram-fuzzy-search"
description: "Implement PostgreSQL trigram similarity fuzzy text search with automatic SQLite fallback. Use when building search features that need fuzzy matching with Postgres pg_trgm optimization but must gracefully degrade to ILIKE for SQLite testing."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

When building search features in SQLAlchemy/FastAPI projects that need:
- Fuzzy text matching with PostgreSQL pg_trgm extension
- Automatic fallback to ILIKE for SQLite (testing)
- Consistent behavior across both database engines
- Better user experience with typo-tolerant search

## Procedure

### 1. Create the similarity-based query

```python
from sqlalchemy import select, func

async def search_products(db, query, limit=10):
    """Search with trigram similarity for Postgres, ILIKE fallback for SQLite."""
    
    stmt = (
        select(Product)
        .where(
            Product.name.isnot(None),
            Product.carbs_100g.isnot(None),  # Optional: filter for data completeness
        )
        .order_by(
            func.similarity(Product.name, query).desc(),
            Product.nutriscore_score.asc().nullslast(),  # Secondary ordering
        )
        .limit(limit)
    )
    
    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception:
        # Fallback for databases without pg_trgm extension
        stmt = (
            select(Product)
            .where(
                Product.name.ilike(f"%{query}%"),
                Product.carbs_100g.isnot(None),
            )
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
```

### 2. Ensure trigram index exists (migration)

```sql
-- In your migration file
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_products_name_trgm ON products USING gin (product_name gin_trgm_ops);
```

Or in Alembic:

```python
from alembic import op

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_products_name_trgm",
        "products",
        ["product_name"],
        postgresql_using="gin",
        postgresql_ops={"product_name": "gin_trgm_ops"},
    )
```

### 3. Normalize results consistently

Always return normalized dictionaries from both paths:

```python
def normalize_product(product):
    """Convert ORM model to normalized dict."""
    return {
        "source": "local",
        "name": product.product_name,
        "brand": product.brands,
        "barcode": product.code,
        "carbs_per_100g": product.carbs_100g,
        "protein_per_100g": product.proteins_100g,
        "fat_per_100g": product.fat_100g,
        "calories_per_100g": product.energy_kcal_100g,
        "serving_size": product.serving_size,
    }
```

## Pitfalls

1. **Trigram extension not installed**: The similarity function will throw an error if `pg_trgm` isn't enabled. The try/except fallback handles this gracefully.

2. **SQLite compatibility**: Tests using SQLite won't have `func.similarity`, so the fallback ILIKE path must work correctly.

3. **Index requirements**: Without the trigram index, similarity queries will be slow. Always create the index in production migrations.

4. **Null handling**: Always filter with `.isnot(None)` before similarity to avoid null-related surprises.

5. **Case sensitivity**: PostgreSQL similarity is case-insensitive, ILIKE is case-insensitive too, so this is consistent.

## Verification

```python
# Test with real Postgres
import asyncio
from sqlalchemy import text

async def test_similarity():
    # Verify trigram works
    result = await db.execute(
        text("SELECT similarity('oats', 'rolled oats')")
    )
    similarity_value = result.scalar()
    assert similarity_value > 0.3, "Similarity should be substantial for word inclusion"
    
    # Test the full search function
    results = await search_products(db, "oats", limit=5)
    assert len(results) > 0, "Should find oats products"
```