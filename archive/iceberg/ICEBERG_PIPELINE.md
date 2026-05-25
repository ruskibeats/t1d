# Iceberg Data Pipeline for Open Food Facts

## Overview
This document describes the Iceberg implementation for T1D-optimized Open Food Facts data.

## Iceberg Table Schema

The `openfoodfacts.products_t1d` table contains:

| Column | Type | Description |
|--------|------|-------------|
| code | string (required) | Product barcode |
| product_name | string | Product name |
| brands | string | Brand names |
| categories | string | Categories |
| categories_tags | list<string> | Category tags |
| countries_tags | list<string> | Country availability |
| serving_size | string | Original serving size text |
| serving_quantity | double | Serving quantity |
| serving_size_grams | double | Parsed serving size in grams |
| carbs_100g | double | Carbs per 100g (validated 0-300g) |
| sugars_100g | double | Sugars per 100g |
| fiber_100g | double | Fiber per 100g |
| proteins_100g | double | Proteins per 100g |
| fat_100g | double | Fat per 100g |
| saturated_fat_100g | double | Saturated fat per 100g |
| energy_kcal_100g | double | Energy in kcal per 100g |
| salt_100g | double | Salt per 100g |
| sodium_100g | double | Sodium per 100g |
| glycemic_index | int | GI placeholder for enrichment |
| glycemic_load_per_serving | double | GL placeholder |
| nutriscore_grade | string | Nutri-Score grade (A-E) |
| nutriscore_score | int | Nutri-Score score |
| nova_group | int | NOVA processing group |
| data_quality_tags | list<string> | OFF quality tags |
| source_updated_at | timestamp | Last update time |
| imported_at | timestamp | Import timestamp |
| quality_score | double | Computed quality 0-1 |
| quality_flags | list<string> | Quality issues detected |

## Quality Validation Rules

1. **Carbs Validation**: Must be between 0-300g per 100g
2. **Serving Size Parsing**: Converts text to grams using regex patterns:
   - g/grams → direct
   - mg → /1000
   - oz → × 28.3495
   - lb → × 453.592
   - ml → direct (assumes water-equivalent)
   - l → × 1000
   - kg → × 1000
3. **Quality Score**: Computed based on:
   - Has carbs: +0.4
   - Has calories: +0.1
   - Has protein: +0.1
   - Has fat: +0.1
   - Has serving size: +0.2
   - Nutri-Score A/B: +0.1
   - Each quality flag: -0.05

## Query Patterns

### Using PyIceberg
```python
from pyiceberg.catalog import load_catalog

catalog = load_catalog(
    "default",
    type="rest",
    uri="http://192.168.0.248:8182",
    warehouse="file:///tmp/iceberg/openfoodfacts"
)

table = catalog.load_table("openfoodfacts.products_t1d")
df = table.scan().to_arrow().to_pandas()
```

### Using Spark
```scala
val df = spark.read.format("iceberg")
  .load("openfoodfacts.products_t1d")

// Filter high-quality items
val qualityFoods = df.filter(col("quality_score") > 0.7)

// Find items with parsed serving sizes
val withServing = df.filter(col("serving_size_grams").isNotNull)
```

### Using Polars
```python
import polars as pl

# Read from Iceberg directory (if Spark/Polars Iceberg support available)
df = pl.scan_parquet("/tmp/iceberg/openfoodfacts/products_t1d/*.parquet")
```

## Running the Import

```bash
cd /root/t1d
source venv/bin/activate

# Full import (2.2M+ records)
python scripts/iceberg_import_off.py

# Test with limit
python scripts/iceberg_import_off.py --limit 1000

# Using different catalog
python scripts/iceberg_import_off.py --catalog-uri http://localhost:8182
```

## Current Results (2.6M records imported)

### Data Quality Metrics
| Metric | Value |
|--------|-------|
| Total records | 2,601,100 |
| Records with carbs | 2,568,514 (98.7%) |
| Records with parsed serving_size_grams | 869,235 (33.4%) |
| Records with original serving_size | 872,073 (33.5%) |
| Mean quality score | 0.738 |
| High quality (score > 0.7) | 1,009,848 (38.8%) |
| Data files created | 54 |

### Improvements Over PostgreSQL
1. **Serving size parsing**: 869k parsed vs 717k raw (21% improvement)
2. **Quality score**: All records scored 0.1-1.0 for ranking/filtering
3. **GI/GL columns**: Ready for enrichment (currently null placeholders)
4. **Time travel**: Iceberg snapshots enable historical queries

### Query Examples with Pandas Filtering
```python
from pyiceberg.catalog import load_catalog

catalog = load_catalog("default", type="rest", uri="http://192.168.0.248:8182")
table = catalog.load_table("openfoodfacts.products_t1d")
df = table.scan().to_arrow().to_pandas()

# High-quality items with serving sizes
excellent = df[(df['quality_score'] > 0.7) & (df['serving_size_grams'].notna())]

# Items matching a search term  
bread = df[df['product_name'].str.contains('bread', case=False, na=False)]

# Sort by quality
top_quality = df.nlargest(100, 'quality_score')
```

## Next Steps

1. **GI Enrichment**: Add glycemic index data from academic sources
2. **Brand Normalization**: Clean and standardize brand names
3. **Category Hierarchy**: Build category taxonomy for better search
4. **Snapshot Management**: Implement time-travel for data versioning