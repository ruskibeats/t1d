---
name: "graph-edge-confidence-provenance"
description: "Build and extend graph edge provenance tracking with ConfidenceComponents decomposition, detector versioning, and provenance payload construction. Use when adding new edge detectors or improving existing confidence scoring."
version: 4
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

Use this skill when you need to:
- Create a new graph edge detector that writes to `health_metric_edges`
- Add provenance tracking to an existing detector
- Decompose confidence scores into interpretable components
- Add detector version tracking for edge lineage
- Build or extend the `ConfidenceComponents` scoring model

## Architecture

Every graph edge producer follows a standard pattern:

```
Detector analysis → ConfidenceComponents → Confidence score → Provenance → Edge
                              │
                              ▼
                     confidence_components_json (stored on edge)
                     provenance_json (stored on edge)
```

## Files

- `app/metrics/confidence_scoring.py` — `ConfidenceComponents`, `build_provenance()`, `categorize_confidence()`
- `app/metrics/detector_versions.py` — `DETECTOR_VERSIONS` dict, `get_detector_version()`, `bump_detector_version()`
- `app/metrics/types.py` — `GraphEdgeType` enum (edges must match existing types)

## Step-by-Step: Adding a New Edge Detector

### 1. Register the edge type (if new)
Add value to `GraphEdgeType` enum in `app/metrics/types.py`.

### 2. Add detector version
```python
# In app/metrics/detector_versions.py
DETECTOR_VERSIONS["your_new_edge_type"] = "1.0.0"
```

### 3. Compute confidence components (full approach)
Use `ConfidenceComponents` dataclass with four weighted dimensions:
- `pattern_strength` (40%) — How strong is the pattern match (0-1)
- `temporal_alignment` (30%) — Time window match quality (0-1)
- `effect_magnitude` (20%) — Size of the effect (0-1)
- `data_quality` (10%) — Completeness of data (0-1)

Weights sum to 1.0. Adjust weights based on which factors are most diagnostic for your detector.

```python
from app.metrics.confidence_scoring import (
    ConfidenceComponents,
    build_provenance,
    categorize_confidence,
)
from app.metrics.detector_versions import get_detector_version

components = ConfidenceComponents(
    pattern_strength=0.85,
    temporal_alignment=0.90,
    effect_magnitude=0.75,
    data_quality=0.95,
)
confidence = components.combined_score()  # weighted sum
provenance = build_provenance(
    detector_name="meal_to_glucose_spike",
    detector_version=get_detector_version("meal_to_glucose_spike"),
    components=components,
    extras={"source_algorithm": "adjacent_reading_comparison"},
)
```

### 4. OR compute confidence (simple approach)
For simpler detectors, use a direct heuristic instead of ConfidenceComponents.
Choose the formula style based on what your detector measures:

**Magnitude-based** (used in exercise, insulin detectors):
```python
confidence = min(abs(effect_magnitude) / 100, 1.0)  # Capped at 1.0
```
Use when the signal is an absolute change (e.g., glucose delta in mg/dL). Divide by 100 to normalize since 100 mg/dL is a clinically significant change.

**Severity/likelihood-based** (used in overnight hypo detector):
```python
confidence = min((threshold - measured_value) / threshold, 1.0)  # Capped at 1.0
```
Use when the signal measures how far a value is from a clinical threshold (e.g., how far below HYPO_THRESHOLD). The further below threshold, the more confident.

**Category-based split**:
```python
if some_value < threshold:
    confidence = 0.9  # Strong signal
else:
    confidence = 0.6  # Weak signal
```
Use when the detector has discrete outcome categories.

| Detector | Formula Style | Rationale |
|----------|--------------|-----------|
| Meal spike | ConfidenceComponents (full) | Multiple factors (timing, magnitude, trend) |
| Exercise impact | Magnitude: `min(abs(change)/100, 1.0)` | Single numeric glucose change value |
| Overnight hypo | Severity: `min((70 - lowest)/70, 1.0)` | Distance below hypo threshold (70 mg/dL) |
| Insulin correlation | Magnitude: `min(abs(change)/100, 1.0)` | Single numeric glucose change value |

### 5. Create the edge

#### Full approach (with ConfidenceComponents)
When writing the edge to `HealthMetricEdge`, set:
- `confidence` = `components.combined_score()`
- `confidence_components_json` = `components.to_dict()`
- `provenance_json` = `provenance` (the build_provenance output)

#### Simple approach (algorithm + evidence string)
When writing the edge without ConfidenceComponents, use:
- `algorithm` = `"pattern_service.detector_name.v1"` (versioned string)
- `evidence` = dict with numeric and categorical fields
- No `confidence_components_json` or `provenance_json` needed

#### Conditional edge type selection
If a single detector can produce **multiple edge types** based on the computed outcome, select the type conditionally:

```python
# Example: exercise can cause DROP or RISE depending on direction
edge_type = (
    GraphEdgeType.EXERCISE_TO_GLUCOSE_DROP
    if computed_change < -15
    else GraphEdgeType.EXERCISE_TO_GLUCOSE_RISE
)
```

The threshold represents the minimum clinically meaningful effect. Use a value specific to your detector's domain (e.g., -15 mg/dL for exercise, not a generic default).

### 6. Wire the edge persistence in PatternService

All edge producers in `app/services/pattern_service.py` follow the same code pattern:

```
analysis computation → _nearest_metric lookup → upsert_edge → warning on failure
```

#### Tolerance minutes: source vs target asymmetry

Source metric tolerance should be **wider** than target (glucose) tolerance because events (exercise, sleep, meals) are logged at coarser granularity than CGM readings.

| Source Type | Source Tolerance | Target (Glucose) Tolerance | Rationale |
|-------------|-----------------|---------------------------|-----------|
| Meal (carbs/calories) | 30 min | 20 min | Meals logged at ~meal time |
| Exercise minutes | 30 min | 20 min | Exercise sessions span time |
| Sleep hours | 120 min | 20 min | Sleep recorded once per night |
| Insulin bolus | 15 min | 30 min | Insulin metric closer to logged time; glucose effect peaks ~2h later |
| Fat intake | 30 min | 20 min | Meals logged at ~meal time |

#### Edge persistence inside loops

When the analysis method iterates over multiple events (e.g., daily overnight checks, per-exercise analysis, per-insulin-event analysis), nest the entire edge persistence block inside the loop with its own try/except:

```python
for each_event in events:  # or: current += timedelta(days=1)
    try:
        # ... _nearest_metric lookup ...
        # ... upsert_edge ...
    except Exception as e:
        self.logger.warning(f"Failed to persist graph edge: {e}")
    continue  # Still process remaining events
```

This ensures one failed edge write doesn't skip subsequent events in the loop.

#### The standard code template

```python
# After computing analysis results, wrap persistence in try/except:
try:
    # 6a. Local imports (avoid circular imports at module level)
    from app.metrics.graph_service import HealthGraphService
    from app.metrics.models import HealthMetric
    from app.metrics.schemas import HealthMetricEdgeCreate
    from app.metrics.types import GraphEdgeType, MetricType

    # 6b. Find source and target metrics using the _nearest_metric helper
    source_metric = await self._nearest_metric(
        session, user_id,
        [MetricType.SOURCE_METRIC_TYPE],  # e.g. MetricType.EXERCISE_MINUTES
        source_timestamp,
        tolerance_minutes=30               # wider for source
    )
    target_metric = await self._nearest_metric(
        session, user_id,
        [MetricType.TARGET_METRIC_TYPE],  # e.g. MetricType.BLOOD_GLUCOSE
        target_timestamp,
        tolerance_minutes=20               # narrower for target
    )

    # 6c. Guard: both metrics must exist and must be different
    if not source_metric or not target_metric or source_metric.id == target_metric.id:
        return  # or continue (if in a loop)

    # 6d. Calculate time_delay in seconds
    delay = int(
        (target_timestamp.replace(tzinfo=None) - source_timestamp.replace(tzinfo=None)).total_seconds()
    )

    # 6e. Create and upsert the edge
    await HealthGraphService(session).upsert_edge(
        user_id,
        HealthMetricEdgeCreate(
            source_metric_id=source_metric.id,
            target_metric_id=target_metric.id,
            edge_type=GraphEdgeType.YOUR_EDGE_TYPE,   # from types.py
            confidence=min(abs(effect) / 100, 1.0),    # or ConfidenceComponents combined
            time_delay_seconds=delay,
            algorithm="pattern_service.your_detector.v1",  # versioned string
            evidence={
                "raw_value_1": round(value, 1),
                "computed_metric": round(result, 1),
                "category_label": category,
            },
        ),
    )
except Exception as e:
    self.logger.warning(f"Failed to persist {edge_name} graph edge: {e}")
```

#### Algorithm naming convention

Use dots with three segments: `pattern_service.{detector_name}.{version}`

| Edge | algorithm value |
|------|----------------|
| MEAL_TO_GLUCOSE_SPIKE | `pattern_service.post_meal_spike.v1` |
| EXERCISE_TO_GLUCOSE_DROP | `pattern_service.exercise_impact.v1` |
| SLEEP_TO_NEXT_DAY_GLUCOSE | `pattern_service.overnight_hypo.v1` |
| INSULIN_TO_GLUCOSE_CHANGE | `pattern_service.insulin_correlation.v1` |
| FOOD_TO_CRASH | `pattern_service.fat_correlation.v1` |

#### Evidence dict conventions

Include fields that enable post-hoc analysis and UI display:

- **Numeric values**: round to 1 decimal, use descriptive keys (`"lowest_value"`, `"glucose_change"`)
- **Categorical**: severity labels, impact types (`"severity"`, `"impact_type"`)
- **Counts when relevant**: `"low_count": len(low_readings)`
- **Duration/percentage**: `"percentage_of_night": round(duration, 1)`

#### The _nearest_metric helper

Already exists in `PatternService` (refactored out of meal spike edge code):

```python
async def _nearest_metric(
    self, session: AsyncSession, user_id: int,
    metric_types: list, target_time: datetime,
    tolerance_minutes: int,
) -> Optional[HealthMetric]:
    """Find nearest HealthMetric of any given type around a timestamp."""
    # Queries HealthMetric for matching type within tolerance window
    # Returns the closest metric by absolute time difference
```

### 7. Add the correlation to the public method output

After the edge persists, also append to the correlation list (if applicable):

```python
correlation_strength = change_count / total_events if total_events > 0 else 0
correlations.append(PatternCorrelation(
    event_type="your_type",
    correlation_strength=round(correlation_strength, 2),
    description=f"{change_count} of {total_events} events followed by outcome",
    statistical_significance=0.05 if change_count > 0 else 1.0,
))
```

## Confidence Categorization for UI/RAG

```python
from app.metrics.confidence_scoring import categorize_confidence

label = categorize_confidence(0.75)  # → "medium"
```

Thresholds: <0.6 = "low", <0.8 = "medium", >=0.8 = "high"

## Bumping Detector Versions

Bump the version when algorithm changes that affect confidence scoring:
```python
from app.metrics.detector_versions import bump_detector_version
bump_detector_version("meal_to_glucose_spike", "1.1.0")
```

## Testing Recommendations

- `tests/test_graph_confidence.py` — test `ConfidenceComponents.to_dict()`, `combined_score()`, `build_provenance()`, `categorize_confidence()`
- Use `pytest.approx()` for float equality checks
- Test empty extras, edge case confidence values (0, 1, boundary thresholds)
- Test that `confidence_components_json` and `provenance_json` are serialized correctly in edge creation

## Key Design Decisions

1. **Weighted sum** over multiplication — allows individual components to be zero without collapsing the score
2. **Components stored as JSON** on the edge — enables post-hoc analysis of why a particular edge scored the way it did
3. **Version in provenance** — enables auditing: was this edge created by v1 or v2 of the detector?
4. **Provenance as JSONB** — flexible schema that can grow as detectors add new metadata