# Database & Graph Architecture

## Overview

T1D Companion uses a single **PostgreSQL** relational database. All patient data lives here, organized by `user_id`. The **health metrics graph** is a derived index — observational edges computed by pattern detection algorithms, stored in the same database, and used as RAG evidence in LLM conversations.

---

## Database Schema

### Core Tables

| Table | Purpose | Key Columns |
|---|---|---|
| `tbl_users` | Authentication, profile, CGM provider config | email, diabetes_type, dexcom_*, nightscout_*, librelinkup_* |
| `tbl_glucose_readings` | Raw CGM readings from any source | user_id, timestamp, glucose_value, source, trend |
| `tbl_context_events` | Meals, insulin, exercise entries | user_id, event_type, carbs_grams, insulin_units, intensity |
| `tbl_conversations` | AI chat sessions | user_id, title |
| `tbl_conversation_messages` | Individual chat messages | conversation_id, role, content |
| `tbl_pattern_analyses` | Stored pattern analysis results | user_id, pattern_type, findings, statistics |

### Unified Health Metrics Store

| Table | Purpose |
|---|---|
| `health_metrics` | Single unified table for ALL measurement types (glucose, carbs, steps, HR, sleep, weight, mood, stress, caffeine, etc.) |
| `health_metric_edges` | Directed observational relationships between two metrics (the graph) |
| `health_daily_aggregates` | Daily rollup summaries per metric type |

### Domain-Specific Tables

These supplement the unified store with domain-specific fields:

| Domain | Tables |
|---|---|
| Food | `foods`, `food_entries` |
| Exercise | `exercise_entries`, `exercise_entry_sets` |
| Sleep | `sleep_entries`, `sleep_stages` |
| Heart | `heart_rate_entries` |
| Blood Pressure | `blood_pressure_entries` |
| Activity | `activity_entries` |
| Body Composition | `body_composition_entries` |
| Fasting | `fasting_entries` |
| Mood | `mood_entries` |
| Water | `water_entries` |
| Environment | `environment_entries` |
| Lifestyle | `lifestyle_entries` |
| Body Battery | `body_battery_entries` |
| Vitals | `vital_entries` |
| Measurements | `custom_measurements` |

---

## Data Flow

```
CGM APIs (Dexcom / Nightscout / LibreLinkUp)
  wearables (Fitbit / Garmin / Withings / Strava / Polar)
  manual entry (API / frontend)
         │
         ▼
   health_metrics           ◄── raw measurements (nodes)
   tbl_glucose_readings          CGM-specific readings
   tbl_context_events            meal/insulin/exercise events
         │
         ▼
   PatternService           ◄── runs detection algorithms
         │
         ├─ detect_post_meal_spikes()
         ├─ detect_overnight_hypoglycemia()
         ├─ analyze_exercise_impact()
         ├─ detect_delayed_high_fat_effects()
         ├─ analyze_correlations()
         └─ link_event_group()
         │
         ▼
   health_metric_edges      ◄── edges with confidence scores
         │
         ▼
   LLM Conversation         ◄── edges used as RAG evidence
```

---

## The Health Metrics Graph

### Architecture

The graph lives in `app/metrics/graph_service.py` (`HealthGraphService`).

- **Nodes**: rows in `health_metrics` (each is a single measurement with a type, value, unit, and timestamp)
- **Edges**: rows in `health_metric_edges` (directed relationships between two metrics)
- **Scoped**: every node and edge is owned by a single `user_id`
- **Observational only**: edges are evidence of temporal/correlational patterns, never medical advice

### Known Graph Edge Types

```python
MEAL_TO_GLUCOSE_SPIKE      # Carbs followed by glucose rise
MEAL_TO_DELAYED_SPIKE      # High-fat meal followed by delayed spike
EXERCISE_TO_GLUCOSE_DROP   # Exercise followed by lower glucose
EXERCISE_TO_GLUCOSE_RISE   # Exercise followed by higher glucose
INSULIN_TO_GLUCOSE_CHANGE  # Insulin followed by glucose change
SLEEP_TO_NEXT_DAY_GLUCOSE  # Sleep association with next-day glucose
STRESS_TO_GLUCOSE_RISE     # Stress followed by glucose rise
HEART_RATE_TO_LOW_GLUCOSE  # Elevated HR preceding low glucose
HYDRATION_TO_GLUCOSE_STABILITY  # Hydration correlating with stable glucose
CORRELATES_WITH            # General temporal correlation
PRECEDES                   # Temporal ordering, no direct causation
SAME_EVENT_AS              # Metrics logged as part of the same event/meal
```

### How Pattern Detection Works

Each detection method in `app/services/pattern_service.py` follows the same pattern:

1. **Query** `health_metrics` for relevant metric types (e.g. carbs + blood_glucose)
2. **Find temporal pairs** using configurable time windows (e.g. 3 hours for post-meal spikes)
3. **Calculate confidence** using decomposed components:

   ```
   confidence = pattern_strength × 0.4
              + temporal_alignment × 0.3
              + effect_magnitude × 0.2
              + data_quality × 0.1
   ```

4. **Upsert** an edge to `health_metric_edges` with:
   - `edge_type`: the relationship type
   - `confidence`: 0.0 – 1.0
   - `algorithm`: e.g. `"pattern_service.post_meal_spike.v1"`
   - `evidence`: measured values, baseline/peak, change amount, time delay
   - `provenance`: detector name, version, timestamp
   - `confidence_components`: the decomposed weights for transparency

5. **Wrap in try/except** so failed edge persistence never crashes detection

### Graph Query Methods

`HealthGraphService` provides these query methods:

| Method | Returns |
|---|---|
| `create_edge()` | New edge (fails if duplicate) |
| `upsert_edge()` | Create or update (merges evidence, keeps max confidence) |
| `query_edges()` | Filtered edges (by type, confidence, source/target) |
| `get_neighbors()` | All edges touching a metric (incoming + outgoing) |
| `get_causes()` | Incoming edges (what caused this metric) |
| `get_effects()` | Outgoing edges (what this metric caused) |
| `get_strongest_edges()` | Top edges by confidence |
| `get_subgraph()` | BFS traversal up to depth 3 around a metric |
| `link_event_group()` | Pairwise SAME_EVENT_AS edges for an event group |
| `get_edge_statistics()` | Count + average confidence |

---

## RAG Integration

When a user asks a question:

1. The **strongest edges** (by confidence) matching the conversation context are retrieved
2. The edges' evidence payloads are formatted as structured context
3. The LLM receives this context alongside the safety system prompt
4. The LLM generates a response grounded in the observational evidence

**Guardrails**: The SafetyAgent checks both input and output. Dosing/treatment questions are caught. All responses include the disclaimer: *"Educational insights, not medical advice."*

---

## Metrics Types (Unified Store)

The `MetricType` enum (`app/metrics/types.py`) defines ~60 metric types across 10 categories:

| Category | Examples |
|---|---|
| Glucose & Insulin | blood_glucose, insulin, insulin_basal, insulin_bolus, cgm_trend, estimated_a1c |
| Nutrition | carbs, protein, fat, fiber, calories, glycemic_index, glycemic_load, water, caffeine |
| Exercise | exercise_minutes, exercise_calories, steps, distance_km |
| Heart & Vitals | heart_rate, resting_heart_rate, hrv, spo2, blood_pressure_* |
| Sleep | sleep_hours, sleep_deep, sleep_rem, sleep_light, sleep_score |
| Body Composition | weight, body_fat_percent, bmi, lean_mass |
| Fasting & Lifestyle | fasting_duration, mood_score, stress_level, energy_level |
| Lipids | cholesterol_total, cholesterol_hdl, cholesterol_ldl, triglycerides |
| Environment | temperature, humidity, altitude |
| Custom | custom |

---

## Key Files

| File | Purpose |
|---|---|
| `app/db/models.py` | SQLAlchemy ORM models (User, GlucoseReading, ContextEvent, Conversation) |
| `app/metrics/models.py` | Unified metric store models (HealthMetric, HealthMetricEdge, HealthDailyAggregate) |
| `app/metrics/types.py` | MetricType and GraphEdgeType enums |
| `app/metrics/graph_service.py` | HealthGraphService — graph operations |
| `app/metrics/schemas.py` | Pydantic schemas for edges (HealthMetricEdgeCreate, HealthMetricEdgeQuery) |
| `app/services/pattern_service.py` | Pattern detection algorithms that create graph edges |
| `app/services/llm_service.py` | LLM integration with RAG context assembly |
| `app/agents/safety_agent.py` | Safety guardrails + disclaimer enforcement |

---

*Last updated: May 2026*