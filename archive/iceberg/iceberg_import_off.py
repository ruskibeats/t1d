"""Stream Open Food Facts JSONL to Iceberg with validation and data quality improvements.

This script:
1. Reads the compressed JSONL stream row by row (memory efficient)
2. Validates carbs range (0-300g per 100g)
3. Parses serving_size to standard units (grams)
4. Adds placeholder GI/GL columns for enrichment
5. Writes to Iceberg table via pyiceberg in batches

The output is optimized for T1D use cases with quality filtering.
"""

from __future__ import annotations

import argparse
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField,
    StringType,
    IntegerType,
    DoubleType,
    TimestampType,
    ListType,
)

# Carbs validation bounds (per 100g)
CARBS_MIN = 0.0
CARBS_MAX = 300.0

# Regex patterns for serving size parsing
SERVING_PATTERNS = [
    (r"(\d+(?:\.\d+)?)\s*g(?:ram)?s?", "grams", lambda m: float(m.group(1))),
    (r"(\d+(?:\.\d+)?)\s*mg(?:ram)?s?", "mg", lambda m: float(m.group(1)) / 1000),
    (r"(\d+(?:\.\d+)?)\s*oz", "oz", lambda m: float(m.group(1)) * 28.3495),
    (r"(\d+(?:\.\d+)?)\s*lb(?:lbs)?", "lb", lambda m: float(m.group(1)) * 453.592),
    (r"(\d+(?:\.\d+)?)\s*ml", "ml", lambda m: float(m.group(1))),
    (r"(\d+(?:\.\d+)?)\s*l", "l", lambda m: float(m.group(1)) * 1000),
    (r"(\d+(?:\.\d+)?)\s*kg", "kg", lambda m: float(m.group(1)) * 1000),
]

# PyArrow schema for T1D-optimized Open Food Facts data
PA_SCHEMA = pa.schema([
    pa.field("code", pa.string(), nullable=False),
    pa.field("product_name", pa.string()),
    pa.field("brands", pa.string()),
    pa.field("categories", pa.string()),
    pa.field("categories_tags", pa.list_(pa.string())),
    pa.field("countries_tags", pa.list_(pa.string())),
    pa.field("serving_size", pa.string()),
    pa.field("serving_quantity", pa.float64()),
    pa.field("serving_size_grams", pa.float64()),
    pa.field("carbs_100g", pa.float64()),
    pa.field("sugars_100g", pa.float64()),
    pa.field("fiber_100g", pa.float64()),
    pa.field("proteins_100g", pa.float64()),
    pa.field("fat_100g", pa.float64()),
    pa.field("saturated_fat_100g", pa.float64()),
    pa.field("energy_kcal_100g", pa.float64()),
    pa.field("salt_100g", pa.float64()),
    pa.field("sodium_100g", pa.float64()),
    pa.field("glycemic_index", pa.int32()),
    pa.field("glycemic_load_per_serving", pa.float64()),
    pa.field("nutriscore_grade", pa.string()),
    pa.field("nutriscore_score", pa.int32()),
    pa.field("nova_group", pa.int32()),
    pa.field("data_quality_tags", pa.list_(pa.string())),
    pa.field("source_updated_at", pa.timestamp("us")),
    pa.field("imported_at", pa.timestamp("us")),
    pa.field("quality_score", pa.float64()),
    pa.field("quality_flags", pa.list_(pa.string())),
])

# Iceberg schema for the table
ICEBERG_SCHEMA = Schema(
    NestedField(required=True, id=1, name="code", field_type=StringType()),
    NestedField(required=False, id=2, name="product_name", field_type=StringType()),
    NestedField(required=False, id=3, name="brands", field_type=StringType()),
    NestedField(required=False, id=4, name="categories", field_type=StringType()),
    NestedField(
        required=False, id=5, name="categories_tags",
        field_type=ListType(element_id=51, element_type=StringType(), element_required=False)
    ),
    NestedField(
        required=False, id=6, name="countries_tags",
        field_type=ListType(element_id=61, element_type=StringType(), element_required=False)
    ),
    NestedField(required=False, id=7, name="serving_size", field_type=StringType()),
    NestedField(required=False, id=8, name="serving_quantity", field_type=DoubleType()),
    NestedField(required=False, id=9, name="serving_size_grams", field_type=DoubleType()),
    NestedField(required=False, id=10, name="carbs_100g", field_type=DoubleType()),
    NestedField(required=False, id=11, name="sugars_100g", field_type=DoubleType()),
    NestedField(required=False, id=12, name="fiber_100g", field_type=DoubleType()),
    NestedField(required=False, id=13, name="proteins_100g", field_type=DoubleType()),
    NestedField(required=False, id=14, name="fat_100g", field_type=DoubleType()),
    NestedField(required=False, id=15, name="saturated_fat_100g", field_type=DoubleType()),
    NestedField(required=False, id=16, name="energy_kcal_100g", field_type=DoubleType()),
    NestedField(required=False, id=17, name="salt_100g", field_type=DoubleType()),
    NestedField(required=False, id=18, name="sodium_100g", field_type=DoubleType()),
    NestedField(required=False, id=19, name="glycemic_index", field_type=IntegerType()),
    NestedField(required=False, id=20, name="glycemic_load_per_serving", field_type=DoubleType()),
    NestedField(required=False, id=21, name="nutriscore_grade", field_type=StringType()),
    NestedField(required=False, id=22, name="nutriscore_score", field_type=IntegerType()),
    NestedField(required=False, id=23, name="nova_group", field_type=IntegerType()),
    NestedField(
        required=False, id=24, name="data_quality_tags",
        field_type=ListType(element_id=241, element_type=StringType(), element_required=False)
    ),
    NestedField(required=False, id=25, name="source_updated_at", field_type=TimestampType()),
    NestedField(required=False, id=26, name="imported_at", field_type=TimestampType()),
    NestedField(required=False, id=27, name="quality_score", field_type=DoubleType()),
    NestedField(
        required=False, id=28, name="quality_flags",
        field_type=ListType(element_id=281, element_type=StringType(), element_required=False)
    ),
)

import re


def parse_serving_size(text: str | None) -> tuple[float | None, list[str]]:
    """Parse serving size text to grams and return quality flags."""
    if not text:
        return None, ["missing_serving_size"]
    
    text_lower = text.lower().strip()
    flags = []
    
    for pattern, unit, converter in SERVING_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            try:
                return converter(match), []
            except (ValueError, TypeError):
                flags.append(f"parse_error_{unit}")
    
    if any(x in text_lower for x in ["piece", "slice", "can", "cup"]):
        flags.append("ambiguous_serving_unit")
    else:
        flags.append("unrecognized_serving_format")
    
    return None, flags


def compute_quality_score(
    has_carbs: bool, has_serving_size: bool, has_calories: bool,
    has_protein: bool, has_fat: bool, flags: list[str], nutriscore: str | None,
) -> float:
    """Compute a quality score 0-1 for the food item."""
    score = 0.0
    if has_carbs:
        score += 0.4
    if has_calories:
        score += 0.1
    if has_protein:
        score += 0.1
    if has_fat:
        score += 0.1
    if has_serving_size:
        score += 0.2
    if nutriscore and nutriscore.upper() in ("A", "B"):
        score += 0.1
    score -= len(flags) * 0.05
    return max(0.0, min(1.0, score))


def validate_carbs(value: float | None) -> tuple[float | None, list[str]]:
    """Validate carbs are in valid range and return flags."""
    flags = []
    if value is None:
        return None, ["missing_carbs"]
    if not CARBS_MIN <= value <= CARBS_MAX:
        flags.append(f"carbs_out_of_range_{value}")
        return None, flags
    return value, flags


def as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() == "null":
            return None
        return stripped
    return str(value)


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def as_text_list(value: Any) -> list[str] | None:
    if not value:
        return None
    if isinstance(value, list):
        items = [as_text(item) for item in value]
        return [item for item in items if item] or None
    text = as_text(value)
    if not text:
        return None
    return [part.strip() for part in text.split(",") if part.strip()] or None


def as_timestamp(value: Any) -> datetime | None:
    seconds = as_int(value)
    if seconds is None:
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def nutrient(nutriments: dict[str, Any], name: str) -> float | None:
    return as_float(nutriments.get(f"{name}_100g"))


def energy_kcal(nutriments: dict[str, Any]) -> float | None:
    kcal = nutrient(nutriments, "energy-kcal")
    if kcal is not None:
        return kcal
    energy = nutrient(nutriments, "energy")
    unit = as_text(nutriments.get("energy_unit"))
    if energy is None:
        return None
    if unit and unit.lower() == "kj":
        return energy / 4.184
    return energy


def transform_product(product: dict[str, Any]) -> dict[str, Any] | None:
    """Transform OFF product to Iceberg row with validation and quality scoring."""
    code = product.get("code") or product.get("_id")
    if not code:
        return None
    
    nutriments = product.get("nutriments") or {}
    
    carbs = validate_carbs(as_float(nutriments.get("carbohydrates_100g")))[0]
    serving_text = product.get("serving_size")
    serving_g, serving_flags = parse_serving_size(serving_text)
    serving_qty = as_float(product.get("serving_quantity"))
    
    quality_flags = list(serving_flags)
    if carbs is None:
        quality_flags.append("no_carbs_data")
    
    quality_score = compute_quality_score(
        has_carbs=carbs is not None,
        has_serving_size=serving_g is not None,
        has_calories=as_float(nutriments.get("energy-kcal_100g")) is not None,
        has_protein=as_float(nutriments.get("proteins_100g")) is not None,
        has_fat=as_float(nutriments.get("fat_100g")) is not None,
        flags=quality_flags,
        nutriscore=product.get("nutriscore_grade"),
    )
    
    if quality_score < 0.1:
        return None
    
    return {
        "code": as_text(code),
        "product_name": as_text(product.get("product_name")),
        "brands": as_text(product.get("brands")),
        "categories": as_text(product.get("categories")),
        "categories_tags": as_text_list(product.get("categories_tags")),
        "countries_tags": as_text_list(product.get("countries_tags")),
        "serving_size": serving_text,
        "serving_quantity": serving_qty,
        "serving_size_grams": serving_g,
        "carbs_100g": carbs,
        "sugars_100g": as_float(nutriments.get("sugars_100g")),
        "fiber_100g": as_float(nutriments.get("fiber_100g")),
        "proteins_100g": as_float(nutriments.get("proteins_100g")),
        "fat_100g": as_float(nutriments.get("fat_100g")),
        "saturated_fat_100g": as_float(nutriments.get("saturated-fat_100g")),
        "energy_kcal_100g": energy_kcal(nutriments),
        "salt_100g": as_float(nutriments.get("salt_100g")),
        "sodium_100g": as_float(nutriments.get("sodium_100g")),
        "glycemic_index": None,
        "glycemic_load_per_serving": None,
        "nutriscore_grade": as_text(product.get("nutriscore_grade")),
        "nutriscore_score": as_int(product.get("nutriscore_score")),
        "nova_group": as_int(product.get("nova_group")),
        "data_quality_tags": as_text_list(product.get("data_quality_tags")),
        "source_updated_at": as_timestamp(product.get("last_modified_t")),
        "imported_at": datetime.now(timezone.utc),
        "quality_score": quality_score,
        "quality_flags": quality_flags,
    }


def iter_validated_records_in_batches(path: Path, batch_size: int = 50000, limit: int | None = None):
    """Stream and validate records in batches from the JSONL file."""
    records_batch = []
    seen = 0
    total_count = 0
    passed_count = 0
    failed_count = 0
    
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                product = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSON on line {line_number}: {exc}") from exc

            record = transform_product(product)
            total_count += 1
            
            if record is not None:
                records_batch.append(record)
                passed_count += 1
                seen += 1
            else:
                failed_count += 1
            
            if len(records_batch) >= batch_size:
                yield records_batch
                records_batch = []
                
                if limit is not None and seen >= limit:
                    break
        
        if records_batch:
            yield records_batch
    
    print(f"Final stats: total={total_count}, passed={passed_count}, failed={failed_count}")


def create_pyarrow_table(records: list[dict]) -> pa.Table:
    """Convert records to PyArrow table matching schema."""
    if not records:
        return pa.table({field.name: pa.array([], type=field.type) for field in PA_SCHEMA})
    
    arrays = {}
    for field in PA_SCHEMA:
        values = [r.get(field.name) for r in records]
        arrays[field.name] = pa.array(values, type=field.type)
    
    return pa.table(arrays, schema=PA_SCHEMA)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/openfoodfacts/openfoodfacts-products.jsonl.gz"))
    parser.add_argument("--catalog-uri", default="http://192.168.0.248:8182")
    parser.add_argument("--namespace", default="openfoodfacts")
    parser.add_argument("--table", default="products_t1d")
    parser.add_argument("--batch-size", type=int, default=50000)
    parser.add_argument("--limit", type=int, help="Limit records for testing")
    args = parser.parse_args()
    
    print(f"Loading catalog from {args.catalog_uri}...")
    catalog = load_catalog(
        "default",
        **{
            "type": "rest",
            "uri": args.catalog_uri,
            "warehouse": f"file:///tmp/iceberg/{args.namespace}",
        }
    )
    
    try:
        catalog.create_namespace(args.namespace)
        print(f"Created namespace: {args.namespace}")
    except Exception:
        print(f"Namespace {args.namespace} already exists")
    
    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")
    
    table_identifier = f"{args.namespace}.{args.table}"
    
    # Create or load table
    try:
        iceberg_table = catalog.load_table(table_identifier)
        print(f"Loaded existing table: {table_identifier}")
    except Exception:
        iceberg_table = catalog.create_table(
            identifier=table_identifier,
            schema=ICEBERG_SCHEMA,
            location=f"file:///tmp/iceberg/{args.namespace}/{args.table}",
        )
        print(f"Created new table: {table_identifier}")
    
    # Process in batches
    total_written = 0
    for batch_num, records in enumerate(iter_validated_records_in_batches(args.input, args.batch_size, args.limit)):
        if not records:
            continue
            
        table = create_pyarrow_table(records)
        iceberg_table.append(df=table)
        total_written += len(records)
        print(f"Batch {batch_num + 1}: Wrote {len(records)} records (total: {total_written})")
        
        if args.limit is not None and total_written >= args.limit:
            break
    
    print(f"Successfully wrote {total_written} records to {table_identifier}")


if __name__ == "__main__":
    main()