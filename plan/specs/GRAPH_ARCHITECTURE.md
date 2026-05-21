# T1D Companion — Central Data Graph Architecture

## Purpose

The central data graph turns the existing unified `health_metrics` feed into a persistent, queryable personal health knowledge graph.

- **Nodes:** rows in `health_metrics`
- **Edges:** rows in `health_metric_edges`
- **Evidence:** JSON metadata explaining why a relationship exists
- **Confidence:** numeric strength from 0.0 to 1.0
- **Time delay:** delay from source metric to target metric, in seconds

This graph is observational and educational. It must never be used to generate autonomous dosing or treatment instructions.

---

## Current Implementation

### Node table: `health_metrics`

Existing polymorphic health fact table:

- `id`
- `user_id`
- `type` (`MetricType` enum)
- `value`
- `unit`
- `measured_at`
- `ended_at`
- `source`
- `provider_id`
- `metadata` JSONB

Examples:

```text
Metric 101: CARBS = 80g at 18:00, source=manual
Metric 102: BLOOD_GLUCOSE = 230mg/dL at 20:00, source=dexcom
Metric 103: EXERCISE_MINUTES = 45min at 17:00, source=garmin
```

### Edge table: `health_metric_edges`

New graph relationship table:

- `id`
- `user_id`
- `source_metric_id`
- `target_metric_id`
- `edge_type`
- `confidence`
- `time_delay_seconds`
- `algorithm`
- `evidence` JSONB
- `created_at`
- `updated_at`

Example:

```text
source_metric_id=101
 target_metric_id=102
 edge_type=meal_to_glucose_spike
 confidence=0.82
 time_delay_seconds=7200
 evidence={
   "food_name": "Pizza",
   "carbs_grams": 80,
   "pre_meal_baseline": 110,
   "peak_value": 230,
   "glucose_rise": 120,
   "time_to_peak_minutes": 120,
   "severity": "moderate"
 }
```

---

## Node & Edge Taxonomy, Event Grouping, Provenance, Confidence

This section makes the health graph explicit and explainable. It defines what a node is, what an edge is, how events group nodes, how provenance is recorded, and how confidence is decomposed.

### Node taxonomy (`health_metrics`)

`health_metrics` stays as the single polymorphic fact table. This section clarifies how we use it as a graph node store.

Each row is one node.

Current implemented fields:

```text
id
user_id
type                -- enum, see MetricType
value               -- numeric measured value
unit
measured_at
ended_at
source              -- dexcom, garmin, manual, apple_health, etc.
provider_id         -- source-specific stable ID if available
metadata            -- raw provider payload / extra fields
created_at
```

Planned graph-readiness fields:

```text
event_group_id      -- nullable UUID grouping related metrics into one event
quality_score       -- optional 0–1 signal/source quality score
provenance          -- optional structured provenance JSON
updated_at          -- optional if nodes become mutable beyond insertion
value_text          -- optional for text-like/custom observations
```

#### Metric type taxonomy

Group metric types into domains to keep the graph navigable:

- **Glucose:** `BLOOD_GLUCOSE`, `CGM_TREND`, `ESTIMATED_A1C`
- **Meals & nutrition:** `CARBS`, `PROTEIN`, `FAT`, `FIBER`, `CALORIES`, `GLYCEMIC_INDEX`, `GLYCEMIC_LOAD`, `WATER`, `CAFFEINE`
- **Insulin:** `INSULIN`, `INSULIN_BOLUS`, `INSULIN_BASAL`, `INSULIN_CORRECTION`
- **Exercise & activity:** `EXERCISE_MINUTES`, `EXERCISE_CALORIES`, `STEPS`, `DISTANCE_KM`, `FLOORS_CLIMBED`
- **Sleep:** `SLEEP_HOURS`, `SLEEP_SCORE`, `SLEEP_DEEP`, `SLEEP_REM`, `SLEEP_LIGHT`, `SLEEP_AWAKE`, `SLEEP_LATENCY`
- **Heart/vitals:** `HEART_RATE`, `RESTING_HEART_RATE`, `HEART_RATE_VARIABILITY`, `SPO2`, `RESPIRATORY_RATE`, `BLOOD_PRESSURE_SYSTOLIC`, `BLOOD_PRESSURE_DIASTOLIC`, `BODY_BATTERY_CHANGE`, `STRESS_LEVEL`
- **Body composition:** `WEIGHT`, `BODY_FAT_PERCENT`, `BMI`, `WAIST_CIRCUMFERENCE`, `LEAN_MASS`
- **Mood & lifestyle:** `MOOD_SCORE`, `ENERGY_LEVEL`, `FASTING_DURATION`, `CUSTOM`
- **Environment:** `TEMPERATURE`, `HUMIDITY`, `ALTITUDE`
- **Aggregates (optional/future):** `DAILY_TIR`, `DAILY_AVG_GLUCOSE`, etc. These may also live in separate feature tables rather than `health_metrics`.

Rules:

- Every health/life fact that might matter for patterns must be representable as one or more `health_metrics` rows.
- Metric types should be stable and documented; add new types through taxonomy updates, not ad-hoc strings.
- Units must be normalized at write time: mg/dL, kg, km, minutes, hours, ml/liters, etc.

### Edge taxonomy (`health_metric_edges`)

`health_metric_edges` stores relationships as directed edges between metric nodes.

Current implemented fields:

```text
id
user_id
source_metric_id
target_metric_id
edge_type
confidence          -- current overall confidence, 0–1
time_delay_seconds  -- target.measured_at - source.measured_at
algorithm
evidence            -- compact evidence JSON
created_at
updated_at
```

Planned graph-readiness fields:

```text
direction                    -- optional explicit direction
confidence_components        -- JSON breakdown of confidence dimensions
window_start
window_end
provenance                   -- structured detector/run provenance JSON
```

#### Edge type taxonomy

Edges are observational. They describe recurring patterns, not causal truth.

Core examples:

- **Meal ↔ glucose**
  - `meal_to_glucose_spike`
  - `meal_to_delayed_spike`
  - `same_event_as` (link macros within a meal event)
- **Exercise ↔ glucose**
  - `exercise_to_glucose_drop`
  - `exercise_to_glucose_rise`
- **Sleep / stress ↔ glucose**
  - `sleep_to_next_day_glucose`
  - `stress_to_glucose_rise`
  - `heart_rate_to_low_glucose`
- **Insulin ↔ glucose**
  - `insulin_to_glucose_change` (historical description only)
- **Temporal relationships**
  - `precedes` (X tends to occur before Y)
  - `correlates_with` (non-directional association)

Rules:

- Edge type names must be explicit and human-meaningful.
- Avoid “cause” in edge type names; use observational terms.
- Add new edge types through documented taxonomy updates.

### Event grouping (`event_group_id`)

Many real-world events are clusters of metrics.

Examples:

- Meal event:
  - `CARBS`, `FAT`, `PROTEIN`, `FIBER`, `CALORIES`, `GLYCEMIC_LOAD`
  - optional meal note, photo, barcode, contextual `ContextEvent`
- Insulin event:
  - `INSULIN`, `INSULIN_BOLUS`, `INSULIN_BASAL`, `INSULIN_CORRECTION`
  - optional site, note, associated meal group
- Exercise session:
  - `EXERCISE_MINUTES`, `HEART_RATE`, calories, steps, distance

Implementation plan:

- Add nullable `event_group_id` (UUID/string) to `health_metrics`.
- When ingesting a grouped event (meal log, pump event, workout), assign one `event_group_id` to all generated metrics.
- Create `same_event_as` edges between metrics in the same `event_group_id` if useful for traversal.

Benefits:

- Makes meal memory easy: “what happened last time I ate this?”
- Simplifies pattern detectors because each real-world event becomes a natural unit.
- Keeps the graph structurally clean and queryable.

### Provenance schema

Every metric and edge must be traceable.

#### Metric provenance

Most metric provenance is already captured directly on `health_metrics`:

- `source`
- `provider_id`
- `metadata`
- `created_at`

Future `provenance` JSON may include:

```json
{
  "ingestion_pipeline_version": "v1.2.0",
  "normalization_fn": "normalize_garmin_hr_v1",
  "source_timezone": "Europe/London",
  "raw_units": "mmol/L"
}
```

#### Edge provenance

Future `provenance` JSON for edges should include:

```json
{
  "detector": "meal_spike_v1",
  "detector_version": "1.0.0",
  "run_type": "backfill|realtime",
  "run_id": "2026-05-18T10:03Z_user123",
  "feature_window": "baseline: 90min pre; outcome: 180min post",
  "code_commit": "git_sha",
  "tests_version": "graph_suite_23"
}
```

Provenance must be sufficient to answer:

- Which detector created this edge?
- On which data window?
- At which code version?

### Confidence schema

Confidence must be decomposed, not a single opaque number.

Future `confidence_components` JSON:

```json
{
  "repetition": 0.9,
  "temporal_consistency": 0.8,
  "effect_size": 0.7,
  "data_completeness": 0.6,
  "source_quality": 0.8,
  "recency": 0.7
}
```

Initial weighting:

- repetition: 0.25
- temporal consistency: 0.20
- effect size: 0.20
- data completeness: 0.15
- source quality: 0.10
- recency: 0.10

Thresholds:

- Edge creation: persist edges with `confidence >= 0.4` to avoid noise.
- UI “Worth watching”: approximately `0.5–0.7`, depending on pattern type.
- “Often” / “recurring” language: require repetition and temporal consistency components both `>= 0.7`.

Language must reflect confidence:

- Low/mid confidence: “sometimes followed by”, “has occasionally been followed by”
- Mid/high confidence: “has often been followed by”, “has been a recurring pattern for you”

Never use language implying certainty or treatment advice.

### Graph API contract: evidence-first

RAG and UI surfaces should use graph service responses that include:

- nodes with type, value, unit, timestamps, source, provider ID
- edges with edge type, direction, confidence, confidence components, time delay, evidence, provenance

Every pattern card or AI explanation must be able to point to:

- which nodes are involved
- which edges connect them
- what evidence was used
- how confident we are

This matches the broader explainable-AI direction for health knowledge graphs: expose human-interpretable relational evidence, not just model scores.

---

## Edge Types

Defined in `app/metrics/types.py` as `GraphEdgeType`.

| Edge Type | Meaning |
|---|---|
| `meal_to_glucose_spike` | Meal/nutrition metric followed by glucose spike |
| `meal_to_delayed_spike` | High-fat/calorie meal followed by delayed spike |
| `exercise_to_glucose_drop` | Exercise metric followed by lower glucose |
| `exercise_to_glucose_rise` | Exercise metric followed by higher glucose |
| `insulin_to_glucose_change` | Insulin metric followed by glucose change |
| `sleep_to_next_day_glucose` | Sleep metric associated with next-day glucose pattern |
| `stress_to_glucose_rise` | Stress metric associated with glucose rise |
| `heart_rate_to_low_glucose` | Heart/vitals metric associated with low glucose |
| `hydration_to_glucose_stability` | Hydration associated with more stable glucose |
| `correlates_with` | Generic correlation |
| `precedes` | Generic temporal precedence |
| `same_event_as` | Metrics that belong to the same real-world event |

---

## Service Layer

`app/metrics/graph_service.py` exposes `HealthGraphService`:

- `create_edge(user_id, data)`
- `upsert_edge(user_id, data)`
- `query_edges(user_id, params)`
- `get_neighbors(user_id, metric_id)`
- `get_causes(user_id, metric_id)`
- `get_effects(user_id, metric_id)`
- `get_strongest_edges(user_id, edge_types=None, limit=20)`
- `get_subgraph(user_id, center_metric_id, depth=1)`

All methods are user-scoped and verify metric ownership before linking nodes.

---

## API Layer

Graph endpoints are mounted under `/api/v1/metrics/graph`:

- `POST /api/v1/metrics/graph/edges`
- `GET /api/v1/metrics/graph/edges`
- `GET /api/v1/metrics/graph/metrics/{metric_id}/neighbors`
- `GET /api/v1/metrics/graph/metrics/{metric_id}/causes`
- `GET /api/v1/metrics/graph/metrics/{metric_id}/effects`
- `GET /api/v1/metrics/graph/subgraph`
- `GET /api/v1/metrics/graph/recent-correlations`

These currently follow the metrics API's existing `user_id` query parameter pattern.

---

## Pattern Integration

`PatternService.detect_post_meal_spikes()` now optionally persists graph edges.

When a post-meal spike is detected:

1. PatternService finds the nearest nutrition metric (`CARBS` or `CALORIES`) near meal time.
2. PatternService finds the nearest `BLOOD_GLUCOSE` metric near peak time.
3. If both nodes exist, it upserts a `meal_to_glucose_spike` edge.
4. Evidence stores food name, carbs, baseline, peak, glucose rise, time to peak, and severity.

This preserves transient pattern detection as durable graph evidence.

---

## RAG Integration

`LLMService.retrieve_context()` now includes graph edges in `RAGContext.graph_edges`.

`_build_system_prompt()` renders compact graph context like:

```text
Recent Personal Relationship Evidence:
- meal_to_glucose_spike: metric 101 → metric 102 (confidence 0.82, delay 120 min) evidence={...}
```

The prompt explicitly states these relationships are observational evidence only and must not become dosing/treatment instructions.

---

## Tests

Implemented tests:

- `tests/test_health_graph.py`
  - edge create/query
  - upsert/dedup
  - neighbors/causes/effects/subgraph
  - cross-user edge rejection
- `tests/test_api_graph.py`
  - graph API endpoint functions
- `tests/test_pattern_graph_edges.py`
  - post-meal spike detection creates graph edge
- `tests/test_llm_service.py`
  - prompt includes graph edges safely

---

## Remaining Work

1. Add graph persistence for:
   - delayed high-fat meal effects
   - exercise impact
   - overnight low + sleep/heart relationships
   - insulin-to-glucose changes
2. Add frontend graph/explainability surfaces.
3. Add authenticated graph endpoint pattern instead of placeholder `user_id` query param.
4. Add aggregate relationship builder for recurring edges.
5. Add background graph-building jobs for historical backfill.

### PHL/PHKG Research Reference

**Pattern Hierarchy Learning (PHL)** and **Pattern Hierarchical Knowledge Graphs (PHKG)** are research frameworks for building explainable health knowledge graphs:

- **PHL**: Decomposes complex health patterns into hierarchical sub-patterns, enabling interpretable pattern recognition
- **PHKG**: Extends knowledge graphs with hierarchical structure, allowing multi-granularity explanations

Reference: "Pattern Hierarchy Learning for Interpretable Health Knowledge Graphs" - research on hierarchical pattern decomposition for personalized diabetes management.

This informs our `confidence_components` decomposition approach and edge evidence structure.
