# Data Architecture

**Last updated:** 2026-05-25

## Principle

**Single PostgreSQL database for all operational data.** No separate analytics store, no Iceberg layer, no Spark pipeline. PostgreSQL handles everything from MVP to thousands of users.

## What We Store

| Table | Purpose | Scale (per user/month) | Retention |
|-------|---------|----------------------|-----------|
| `tbl_users` | Accounts, auth, profiles | 1 row | Indefinite |
| `tbl_glucose_readings` | CGM readings (288/day) | ~8,640 rows | 90 days |
| `tbl_context_events` | Meals, insulin, exercise | ~100 rows | 90 days |
| `food_entries` | Logged meals | ~90 rows | 90 days |
| `foods` | Personal food items | ~50 rows | Indefinite |
| `openfoodfacts_products` | 2.6M nutrition products | Static (reference) | Indefinite |
| `health_metrics` | Aggregated metrics | ~9,000 rows | 90 days |
| `health_metric_edges` | Graph relationships | ~500 rows | 90 days |
| Domain tables (exercise, sleep, etc.) | Per-domain data | ~50 rows each | 90 days |

**Total per user:** ~18,000 rows/month. At 100 users: ~1.8M rows/month. PostgreSQL handles this with standard indexing.

## Key Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| `glucose_readings` | `(user_id, timestamp)` | Time-range queries |
| `glucose_readings` | `(user_id, timestamp, value)` | TIR calculations |
| `openfoodfacts_products` | `pg_trgm` on `product_name` | Fuzzy food search |
| `food_entries` | `(user_id, entry_date)` | Meal history |
| `health_metrics` | `(user_id, type, measured_at)` | Pattern detection |

## How We Query

| Query | Table | Index Used | Frequency |
|-------|-------|-----------|-----------|
| "Recent glucose" | `glucose_readings` | `(user_id, timestamp)` | Every chat message |
| "TIR for last 14 days" | `glucose_readings` | `(user_id, timestamp)` | Every chat message (cached 10 min) |
| "Find food by name" | `openfoodfacts_products` | `pg_trgm` | Every meal search |
| "Similar historical meals" | `food_history_90d.json` (file) | N/A (in-memory) | Every meal analysis |
| "Pattern detection" | `glucose_readings` + `context_events` | User+timestamp | Nightly batch |

## Scaling Plan

| Users | DB Size | Strategy | Monthly Cost |
|-------|---------|----------|-------------|
| 1-100 | < 2 GB | Single PostgreSQL instance | $10-50 |
| 100-1,000 | 2-20 GB | + TimescaleDB extension for glucose hypertable | $30-100 |
| 1,000-10,000 | 20-200 GB | + Read replica for heavy queries | $100-500 |
| 10,000+ | 200 GB+ | + Partition by time, archive old data to Parquet | $500-2,000 |

## What We Removed (May 2026)

- **Iceberg pipeline** (`scripts/iceberg_import_off.py`, `docs/ICEBERG_PIPELINE.md`) — Archived. Iceberg duplicated OpenFoodFacts data that PostgreSQL already stores and indexes. At current scale (~8 GB total), Iceberg adds infrastructure cost ($200-500/mo for Spark/Trino) with zero benefit. The Postgres `pg_trgm` index on `product_name` serves all food lookup queries in < 50ms.
- **PySpark** — Removed from active dependencies. Available in venv if needed for research/ML but not part of the production stack.

## Migration Path (If Iceberg Is Needed Later)

If the app reaches 10,000+ users and research analytics requires it:

1. Export Postgres tables to Parquet via `COPY (SELECT ...) TO PROGRAM '...'`
2. Load into Iceberg via the archived `scripts/iceberg_import_off.py` pipeline
3. Query via Trino/Spark for analytics (not for production lookups)
4. Production food lookups stay on PostgreSQL (single-row, sub-50ms queries)