---
name: "t1d-synthetic-data-pipeline-guide"
description: "Trace the synthetic data pipeline in T1D Companion: understand how SyntheticDataGenerator creates test data files, how SyntheticIngestionMapper reads Synthea CSV into domain models (User, HealthMetric, ContextEvent), and how the two connect to HealthMetricService. Use when onboarding to T1D, debugging synthetic test data, extending the pipeline, or writing tests that exercise synthetic data."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

Trace and understand the synthetic data generation and ingestion pipeline in the T1D Companion project. Use when:

- Onboarding to the codebase and needing to understand how test/development data is created and loaded
- Debugging why synthetic test data isn't appearing in the database
- Extending the pipeline (adding new metric types, new CSV columns, or new data generators)
- Writing integration tests that exercise the synthetic data pipeline
- Investigating the data flow from raw file on disk through to domain models (User, HealthMetric, ContextEvent)

**Do NOT use** this skill for:
- Tracing production API endpoints to their backend services (use `t1d-api-ingestion-scout` instead)
- Adding new wearable/OAuth ingestion providers (use `wearable-ingestion-provider-add` instead)
- General codebase survey patterns (use `survey-python-package-implementations` instead)

## Procedure

### 1. Locate the Two Core Classes

The synthetic data pipeline has two distinct classes with different responsibilities:

```bash
# Find both classes
grep -rn "class.*Synthetic" app/services/
```

This will find:
- `SyntheticDataGenerator` — *generates* synthetic data files (JSON) on disk under `data/synthetic/`
- `SyntheticIngestionMapper` — *reads and ingests* Synthea CSV data into domain models via the database

Read both source files:

```bash
# Read the generator
read app/services/synthetic_data_generator.py

# Read the ingestion mapper
read app/services/synthetic_ingestion.py
```

### 2. Check Existing Synthetic Data Files

Synthetic data is stored at `data/synthetic/user_{user_id}/` with `profile.json` and `glucose.json`:

```bash
ls -la data/synthetic/
ls data/synthetic/user_1/
```

The glucose JSON format uses 5-minute intervals with fields: `timestamp`, `glucose_value`, `reading_type`, `source`.

### 3. Trace the Data Flow

The pipeline has two independent flows:

**A) Generator Flow (JSON → Disk)**
- `SyntheticDataGenerator.generate_synthetic_user()` — creates profile dict
- `SyntheticDataGenerator.generate_synthetic_glucose()` — creates glucose readings with numpy (sinusoidal pattern + noise)
- `SyntheticDataGenerator.save_data()` — writes `profile.json` and `glucose.json`

**B) Ingestion Mapper Flow (CSV → DB)**
- `SyntheticIngestionMapper.map_patient()` — maps Synthea patient CSV → `User` model (email, full_name, diabetes_type)
- `SyntheticIngestionMapper.map_observation()` — maps Synthea observation CSV → `HealthMetric` via `HealthMetricService.create()` with `MetricType.BLOOD_GLUCOSE`
- `SyntheticIngestionMapper.map_condition()` — maps Synthea condition CSV → `ContextEvent` (e.g., diabetes diagnosis)

### 4. Understand the Domain Model Targets

The mapper uses three different persistence targets:

| CSV Type | Target Model | Persistence Method |
|----------|-------------|-------------------|
| Patient | `User` | `db.add()` + `db.commit()` |
| Observation (Glucose) | `HealthMetric` (via `HealthMetricService`) | `metric_service.create()` |
| Condition | `ContextEvent` | `db.add()` + `db.commit()` |

Notice that **glucose readings go through `HealthMetricService`** (which may add additional processing), while users and conditions are inserted directly. This is a non-obvious routing decision.

### 5. Review Existing Tests

The test file at `tests/test_synthetic_ingestion.py` covers all three mapper methods:

```bash
read tests/test_synthetic_ingestion.py
```

Tests exercise:
- `test_map_patient` — creates a User from CSV row, verifies full_name and email formatting
- `test_map_observation` — creates a HealthMetric, verifies value and type
- `test_map_condition` — creates a ContextEvent, verifies description contains "diabetes"

Each test requires a `db_session` fixture and uses `pytest.mark.asyncio`.

### 6. Run the Tests to Verify

```bash
cd /root/t1d
pytest tests/test_synthetic_ingestion.py -v
```

Expected: all 3 tests pass.

## Pitfalls

- **Two separate systems**: The `SyntheticDataGenerator` writes JSON files to disk; the `SyntheticIngestionMapper` reads CSV files. They are **not** connected — the generator creates test fixtures, the mapper is for importing external Synthea data. Do not assume one feeds the other.
- **Routing through HealthMetricService**: Glucose observations don't go directly to `GlucoseReading` — they go through `HealthMetricService` with `MetricType.BLOOD_GLUCOSE`. This means they end up in the `health_metrics` table, not directly a `glucose_readings` table.
- **String field names**: The mapper uses Synthea-style field names (`'FIRST'`, `'LAST'`, `'DESCRIPTION'`, `'DATE'`). Missing or renamed columns cause `KeyError` silently logged at WARNING level.
- **`metric_service.create()` requires a valid user_id**: The User must already exist in the database before calling `map_observation()` or `map_condition()`.
- **Async session lifecycle**: The mapper receives an `AsyncSession` at construction time. If the session is closed or the transaction is rolled back, all pending inserts are lost.
- **No existing `synthetic_data_exploration.py`**: There is no pre-existing exploration script; if one is expected, it must be created fresh.

## Verification

After following this procedure, you should be able to confirm:

- [ ] Located both `SyntheticDataGenerator` and `SyntheticIngestionMapper` classes
- [ ] Found existing synthetic data files at `data/synthetic/user_{1,2,3}/`
- [ ] Understood the different data flows (generator → JSON files vs mapper → DB from CSV)
- [ ] Identified the three target models: `User`, `HealthMetric`, `ContextEvent`
- [ ] Verified that glucose obs go through `HealthMetricService.create()` not direct DB insert
- [ ] Ran `test_synthetic_ingestion.py` tests and all pass
- [ ] Can describe the data format (5-min intervals, sinusoidal pattern, mg/dL units)