---
name: wearable-ingestion-provider-add
description: "Add a new wearable health data ingestion provider to the T1D Companion project. Covers the 5-provider pattern (Fitbit, Garmin, Withings, Strava, Polar): create service class with parse_* methods mapping provider fields to HealthMetricCreate + MetricType, apply event_group_id for correlated multi-metric events, handle timestamp normalization, register in __init__.py. Use when integrating a new wearable/OAuth health data source."
version: 1
created: 2026-05-19
updated: 2026-05-19
---
# Wearable Ingestion Provider — Add

## When to Use

Use this skill when adding a new wearable/health data ingestion provider to the T1D Companion project. The project has five existing providers following a consistent pattern: **Fitbit**, **Garmin**, **Withings**, **Strava**, and **Polar**. Follow the same conventions when adding a new one (e.g. Apple Health, Oura, Whoop, Samsung Health, Google Fit).

**Trigger signals**: user asks to "add [provider name] ingestion", "integrate [provider name]", "create ingestion service for [provider name]", or mentions a new wearable/OAuth health data source.

**Boundaries**: This skill covers the ingestion service class only (parsing provider data into `HealthMetricCreate` objects). It does NOT cover OAuth flow setup, API client configuration, webhook endpoints, or database migrations — those are separate concerns.

## Procedure

### 1. Create the service file

```bash
touch app/ingestion/{provider}.py
```

Where `{provider}` is the lowercase provider name (e.g., `oura`, `apple_health`, `google_fit`).

### 2. Write the service class

Open `app/ingestion/{provider}.py` and author:

```python
"""{Provider} health data ingestion service.

[Brief description of provider and what data it syncs.]
Maps [provider data types] to the unified HealthMetricCreate format.
"""

from datetime import datetime, timezone
from typing import Any

from app.metrics.schemas import HealthMetricCreate
from app.metrics.types import MetricType


class {Provider}IngestionService:
    """Service for [fetching/parsing] and normalizing {Provider} data.

    Converts {Provider}'s native formats to T1D Companion's normalized
    HealthMetric schema. Each sub-metric is emitted as a separate
    HealthMetricCreate with its own MetricType.
    """

    BASE_URL = "https://api.{provider}.com/v1"  # If applicable

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token
        # If the service needs metric_service, accept it as parameter
        # (see GarminIngestionService for the pattern)
```

#### Key conventions to follow:

| Convention | Rule | Example |
|-----------|------|---------|
| **Class name** | `{Provider}IngestionService` | `FitbitIngestionService`, `OuraIngestionService` |
| **source field** | Lowercase provider name | `source="oura"` |
| **provider_id** | Provider's native ID string | `str(entry.get("id", ""))` |
| **Unit conversion** | Convert to T1D-compatible units | seconds→minutes (`/60`), ms→minutes (`/1000/60`), seconds→hours (`/3600`) |
| **Timestamp** | Always UTC datetime | `datetime.fromisoformat(start.replace("Z", "+00:00"))` or `datetime.fromtimestamp(ts, tz=timezone.utc)` |

### 3. Implement parse_* methods

Add one `parse_*` method per data category the provider supports. Choose `MetricType` values from `app/metrics/types.py`.

#### Common parse methods and metric mappings:

```python
def parse_activities(self, activities: list[dict]) -> list[HealthMetricCreate]:
    """Parse activity/exercise data."""
    ...

def parse_sleep(self, sleep_data: list[dict] | dict) -> list[HealthMetricCreate]:
    """Parse sleep data with optional stages."""
    ...
```

#### Metric mapping reference:

| Data Field | MetricType | Unit |
|-----------|-----------|------|
| Exercise duration | `MetricType.EXERCISE_MINUTES` | `"minutes"` |
| Calories burned | `MetricType.CALORIES` | `"kcal"` |
| Heart rate (avg) | `MetricType.HEART_RATE` | `"bpm"` |
| Distance | `MetricType.DISTANCE_KM` | `"km"` |
| Elevation gain | `MetricType.FLOORS_CLIMBED` | `"meters"` |
| Steps | `MetricType.STEPS` | `"steps"` |
| Sleep hours | `MetricType.SLEEP_HOURS` | `"hours"` |
| Sleep deep | `MetricType.SLEEP_DEEP` | `"hours"` |
| Sleep REM | `MetricType.SLEEP_REM` | `"hours"` |
| Sleep light | `MetricType.SLEEP_LIGHT` | `"hours"` |
| Sleep awake | `MetricType.SLEEP_AWAKE` | `"hours"` or `"minutes"` |
| Sleep score | `MetricType.SLEEP_SCORE` | `"score"` or `"percent"` |
| Weight | `MetricType.WEIGHT` | `"kg"` |
| Body fat % | `MetricType.BODY_FAT_PERCENT` | `"%"` |
| Lean mass | `MetricType.LEAN_MASS` | `"kg"` |
| SpO2 | `MetricType.SPO2` | `"%"` |
| Blood pressure systolic | `MetricType.BLOOD_PRESSURE_SYSTOLIC` | `"mmHg"` |
| Blood pressure diastolic | `MetricType.BLOOD_PRESSURE_DIASTOLIC` | `"mmHg"` |
| HRV | `MetricType.HEART_RATE_VARIABILITY` | `"ms"` |
| Respiratory rate | `MetricType.RESPIRATORY_RATE` | `"breaths/min"` |
| Stress level | `MetricType.STRESS_LEVEL` | `"score"` |
| Mood score | `MetricType.MOOD_SCORE` | `"score"` |
| Energy level | `MetricType.ENERGY_LEVEL` | `"score"` |
| Body battery change | `MetricType.BODY_BATTERY_CHANGE` | `"points"` |

### 4. Apply event_group_id for correlated metrics

When a single provider event produces **multiple related metrics** (e.g., an activity produces EXERCISE_MINUTES + CALORIES + HEART_RATE), assign a **single shared `event_group_id`** to all of them so they are correlated in the database.

```python
# Generate ONE UUID per event group
activity_group_id = str(__import__('uuid').uuid4())

metrics.append(HealthMetricCreate(
    type=MetricType.EXERCISE_MINUTES,
    value=duration_min,
    unit="minutes",
    measured_at=start_time,
    source="{provider}",
    provider_id=activity_id,
    event_group_id=activity_group_id,  # Shared across related metrics
))

metrics.append(HealthMetricCreate(
    type=MetricType.CALORIES,
    value=float(calories),
    unit="kcal",
    measured_at=start_time,
    source="{provider}",
    provider_id=activity_id,
    event_group_id=activity_group_id,  # Same group
))
```

**Do NOT** generate a new UUID per metric — all metrics from the same provider event (same log entry, same sleep session, same workout) share one group ID.

**When NOT to use event_group_id**: For simple single-metric data points (e.g., a standalone weight measurement with no correlated metric), `event_group_id` can be omitted.

### 5. Handle timestamp normalization

Providers use different timestamp formats. Normalize all to Python `datetime` (UTC):

| Provider Format | Parsing Code |
|----------------|-------------|
| ISO with `Z` suffix | `datetime.fromisoformat(date_str.replace("Z", "+00:00"))` |
| Epoch seconds (int) | `datetime.fromtimestamp(epoch_secs, tz=timezone.utc)` |
| ISO without TZ | `datetime.fromisoformat(date_str)` — then verify UTC |
| Custom format | `datetime.strptime(date_str, format_str).replace(tzinfo=timezone.utc)` |

### 6. Add OAuth helpers (if needed)

Providers with OAuth flows should expose static methods:

```python
@staticmethod
def authorize_url(client_id: str, redirect_uri: str) -> str:
    """Build the OAuth authorization URL."""
    return f"https://{provider}.com/oauth2/authorize?..."

@staticmethod
def token_exchange_payload(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """Build the token exchange request payload."""
    return {
        "grant_type": "authorization_code",
        "code": code,
        ...
    }
```

See `FitbitIngestionService` and `StravaIngestionService` for the pattern.

### 7. Register in __init__.py

Add the import and expose in `__all__` in `app/ingestion/__init__.py`:

```python
from app.ingestion.{provider} import {Provider}IngestionService

__all__ = [
    ...,
    "{Provider}IngestionService",
]
```

### 8. Write tests

Create `tests/test_ingestion_{provider}.py` with:

- Test each `parse_*` method with sample provider JSON
- Verify `MetricType` is correct for each output
- Verify `event_group_id` is shared across correlated metrics
- Verify timestamp normalization
- Test empty/malformed input edge cases

## Pitfalls

### Missing metric_type for a field
If a provider exposes a data field with no corresponding `MetricType`, add a new member to the `MetricType` enum in `app/metrics/types.py`. Examples from existing providers: `SLEEP_DEEP`, `SLEEP_REM`, `SLEEP_LIGHT`, `SLEEP_AWAKE`, `BODY_FAT_PERCENT`, `LEAN_MASS`, `DISTANCE_KM`, `FLOORS_CLIMBED`, `HEART_RATE_VARIABILITY`.

### Timestamp timezone-naïve
Provider timestamps often lack timezone info. If the provider docs say UTC, call `.replace(tzinfo=timezone.utc)`. If local time, convert to UTC first. Always verify with the provider API docs.

### Unit mismatch
Providers report in different units (meters vs km, seconds vs minutes, ms vs minutes). Always convert to T1D standard units:
- Duration: **minutes** for exercise, **hours** for sleep
- Distance: **km** (divide meters by 1000)
- Calories: **kcal** (usually already in kcal)
- Weight: **kg** (divide lbs by 2.205 if needed)
- Heart rate: **bpm** (usually already in bpm)

### Forgetting source field
Every `HealthMetricCreate` **must** have `source="{provider}"` (lowercase). Missing source breaks data provenance tracking.

### Overlapping event_group_id per metric
If you generate a new UUID **inside** each metric's constructor call, you'll get a different UUID per metric. That defeats the purpose. Generate the UUID once, assign it to a variable, then pass the same variable to all related metrics.

### Garmin-style dependency injection
If the ingestion service needs to write directly to the database (like Garmin's `ingest_webhook`), take `HealthMetricService` as a constructor dependency. For stateless parsing-only services (Fitbit, Strava, Withings, Polar), keep the constructor simple with just `access_token`.

## Verification

After creating the provider:

1. **Import test**: `python -c "from app.ingestion import {Provider}IngestionService; print('OK')"`
2. **Unit tests pass**: `pytest tests/test_ingestion_{provider}.py -v`
3. **MetricType coverage**: Every field you parse maps to a valid `MetricType` — no placeholder types
4. **event_group_id correlation**: For multi-metric events, query that all metrics share the same group ID
5. **Timestamp coercion**: All output timestamps are `datetime` with UTC timezone
6. **Empty input**: Each `parse_*` method returns `[]` for empty input without crashing