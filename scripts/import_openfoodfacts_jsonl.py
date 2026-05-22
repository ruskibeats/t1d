#!/usr/bin/env python3
"""Stream the Open Food Facts JSONL export into Postgres.

This importer intentionally avoids pandas and never decompresses the full
export to disk. It reads ``openfoodfacts-products.jsonl.gz`` one line at a
time, keeps only the nutrition fields the T1D app needs, and loads batches
through asyncpg COPY into a compact lookup table.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import asyncpg


DEFAULT_INPUT = Path("data/openfoodfacts/openfoodfacts-products.jsonl.gz")
DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/t1d_companion"

COLUMNS = (
    "code",
    "product_name",
    "brands",
    "categories",
    "categories_tags",
    "countries_tags",
    "serving_size",
    "serving_quantity",
    "product_quantity",
    "product_quantity_unit",
    "nutrition_data_per",
    "carbs_100g",
    "sugars_100g",
    "fiber_100g",
    "proteins_100g",
    "fat_100g",
    "saturated_fat_100g",
    "energy_kcal_100g",
    "salt_100g",
    "sodium_100g",
    "nutriscore_grade",
    "nutriscore_score",
    "nova_group",
    "data_quality_tags",
    "source_updated_at",
)


CREATE_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS openfoodfacts_products (
    code text PRIMARY KEY,
    product_name text,
    brands text,
    categories text,
    categories_tags text[],
    countries_tags text[],
    serving_size text,
    serving_quantity double precision,
    product_quantity double precision,
    product_quantity_unit text,
    nutrition_data_per text,
    carbs_100g double precision,
    sugars_100g double precision,
    fiber_100g double precision,
    proteins_100g double precision,
    fat_100g double precision,
    saturated_fat_100g double precision,
    energy_kcal_100g double precision,
    salt_100g double precision,
    sodium_100g double precision,
    nutriscore_grade text,
    nutriscore_score integer,
    nova_group integer,
    data_quality_tags text[],
    source_updated_at timestamptz,
    imported_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_off_products_product_name
    ON openfoodfacts_products (product_name);
CREATE INDEX IF NOT EXISTS ix_off_products_brands
    ON openfoodfacts_products (brands);
CREATE INDEX IF NOT EXISTS ix_off_products_nutrition_carbs
    ON openfoodfacts_products (carbs_100g);
CREATE INDEX IF NOT EXISTS ix_off_products_product_name_trgm
    ON openfoodfacts_products USING gin (product_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_off_products_brands_trgm
    ON openfoodfacts_products USING gin (brands gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_off_products_categories_tags_gin
    ON openfoodfacts_products USING gin (categories_tags);
"""


def database_url_from_env() -> str:
    raw = os.getenv("OPENFOODFACTS_DATABASE_URL") or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    return raw.replace("postgresql+asyncpg://", "postgresql://")


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


def has_nutrition(values: tuple[Any, ...]) -> bool:
    nutrition_start = COLUMNS.index("carbs_100g")
    nutrition_end = COLUMNS.index("sodium_100g") + 1
    return any(value is not None for value in values[nutrition_start:nutrition_end])


def transform_product(product: dict[str, Any], include_no_nutrition: bool) -> tuple[Any, ...] | None:
    code = as_text(product.get("code") or product.get("_id"))
    if not code:
        return None

    nutriments = product.get("nutriments")
    if not isinstance(nutriments, dict):
        nutriments = {}

    values = (
        code,
        as_text(product.get("product_name")),
        as_text(product.get("brands")),
        as_text(product.get("categories")),
        as_text_list(product.get("categories_tags")),
        as_text_list(product.get("countries_tags")),
        as_text(product.get("serving_size")),
        as_float(product.get("serving_quantity")),
        as_float(product.get("product_quantity")),
        as_text(product.get("product_quantity_unit")),
        as_text(product.get("nutrition_data_per")),
        nutrient(nutriments, "carbohydrates"),
        nutrient(nutriments, "sugars"),
        nutrient(nutriments, "fiber"),
        nutrient(nutriments, "proteins"),
        nutrient(nutriments, "fat"),
        nutrient(nutriments, "saturated-fat"),
        energy_kcal(nutriments),
        nutrient(nutriments, "salt"),
        nutrient(nutriments, "sodium"),
        as_text(product.get("nutriscore_grade")),
        as_int(product.get("nutriscore_score")),
        as_int(product.get("nova_group")),
        as_text_list(product.get("data_quality_tags")),
        as_timestamp(product.get("last_modified_t") or product.get("last_updated_t")),
    )
    if not include_no_nutrition and not has_nutrition(values):
        return None
    return values


def iter_records(path: Path, include_no_nutrition: bool, limit: int | None) -> Iterable[tuple[Any, ...]]:
    seen = 0
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                product = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSON on line {line_number}: {exc}") from exc

            record = transform_product(product, include_no_nutrition)
            if record is None:
                continue

            yield record
            seen += 1
            if limit is not None and seen >= limit:
                return


async def flush_batch(conn: asyncpg.Connection, batch: list[tuple[Any, ...]]) -> int:
    if not batch:
        return 0

    await conn.execute("TRUNCATE TABLE openfoodfacts_products_import")
    await conn.copy_records_to_table(
        "openfoodfacts_products_import",
        records=batch,
        columns=COLUMNS,
    )

    column_sql = ", ".join(COLUMNS)
    update_sql = ", ".join(f"{column}=EXCLUDED.{column}" for column in COLUMNS if column != "code")
    result = await conn.execute(
        f"""
        INSERT INTO openfoodfacts_products ({column_sql})
        SELECT DISTINCT ON (code) {column_sql}
        FROM openfoodfacts_products_import
        WHERE code IS NOT NULL
        ORDER BY code
        ON CONFLICT (code) DO UPDATE
        SET {update_sql}, imported_at = now()
        """
    )
    return int(result.split()[-1])


async def import_products(args: argparse.Namespace) -> None:
    input_path = args.input
    if not input_path.exists():
        raise SystemExit(f"Input file does not exist: {input_path}")

    conn = await asyncpg.connect(args.database_url)
    try:
        if args.ensure_schema:
            await conn.execute(CREATE_SCHEMA_SQL)
        if args.replace:
            await conn.execute("TRUNCATE TABLE openfoodfacts_products")

        await conn.execute(
            """
            CREATE TEMP TABLE openfoodfacts_products_import
            (LIKE openfoodfacts_products INCLUDING DEFAULTS)
            ON COMMIT PRESERVE ROWS
            """
        )

        started = time.monotonic()
        batch: list[tuple[Any, ...]] = []
        read_count = 0
        written_count = 0

        for record in iter_records(input_path, args.include_no_nutrition, args.limit):
            batch.append(record)
            read_count += 1
            if len(batch) >= args.batch_size:
                written_count += await flush_batch(conn, batch)
                batch.clear()
                if written_count and written_count % args.progress_every < args.batch_size:
                    elapsed = time.monotonic() - started
                    rate = written_count / elapsed if elapsed else 0
                    print(f"imported={written_count:,} elapsed={elapsed:.1f}s rate={rate:,.0f}/s", flush=True)

        written_count += await flush_batch(conn, batch)
        elapsed = time.monotonic() - started
        print(
            f"done read={read_count:,} imported_or_updated={written_count:,} "
            f"elapsed={elapsed:.1f}s",
            flush=True,
        )
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--database-url", default=database_url_from_env())
    parser.add_argument("--batch-size", type=int, default=10_000)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--progress-every", type=int, default=100_000)
    parser.add_argument("--ensure-schema", action="store_true", help="Create the table and indexes if missing.")
    parser.add_argument("--replace", action="store_true", help="Truncate openfoodfacts_products before importing.")
    parser.add_argument(
        "--include-no-nutrition",
        action="store_true",
        help="Keep products without useful per-100g nutrition fields.",
    )
    return parser.parse_args()


def main() -> None:
    asyncio.run(import_products(parse_args()))


if __name__ == "__main__":
    main()
