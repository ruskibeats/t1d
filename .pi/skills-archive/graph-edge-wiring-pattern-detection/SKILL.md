---
name: graph-edge-wiring-pattern-detection
description: Wire pattern detection methods in PatternService to persist graph edges with proper edge types, confidence calculation, and evidence structure.
---

# Graph Edge Wiring Pattern Detection

## Purpose
Wire pattern detection methods in PatternService to persist graph edges. This is the reusable boilerplate pattern for connecting pattern detectors to the health metrics graph.

## When to Use
When adding a new pattern detection method that should persist observational evidence as graph edges.

## Procedure

### 1. Import necessary modules at the point of use
```python
from app.metrics.graph_service import HealthGraphService
from app.metrics.models import HealthMetric
from app.metrics.schemas import HealthMetricEdgeCreate
from app.metrics.types import GraphEdgeType, MetricType
```

### 2. Find source and target metrics
Use the `_nearest_metric()` helper to find metrics within tolerance:
```python
source_metric = await self._nearest_metric(
    session, user_id, [MetricType.EXERCISE_MINUTES], exercise_time, tolerance_minutes=30
)
target_metric = await self._nearest_metric(
    session, user_id, [MetricType.BLOOD_GLUCOSE], peak_time, tolerance_minutes=20
)
```

### 3. Calculate confidence
```python
confidence = min(abs(change) / 100, 1.0)  # or custom calculation
```

### 4. Upsert edge with evidence
```python
await HealthGraphService(session).upsert_edge(
    user_id,
    HealthMetricEdgeCreate(
        source_metric_id=source_metric.id,
        target_metric_id=target_metric.id,
        edge_type=GraphEdgeType.EXERCISE_TO_GLUCOSE_DROP,
        confidence=confidence,
        time_delay_seconds=delay,
        algorithm="pattern_service.exercise_impact.v1",
        evidence={"exercise_duration": duration, "change": change},
    ),
)
```

### 5. Wrap in try-except for graceful degradation
```python
try:
    # ... edge persistence code ...
except Exception as e:
    self.logger.warning(f"Failed to persist graph edge: {e}")
```

## Key Patterns

### Edge Type Selection
- `meal_to_glucose_spike` - Meal/nutrition followed by glucose spike
- `meal_to_delayed_spike` - High-fat meal followed by delayed spike
- `exercise_to_glucose_drop` - Exercise followed by lower glucose
- `exercise_to_glucose_rise` - Exercise followed by higher glucose
- `insulin_to_glucose_change` - Insulin followed by glucose change
- `sleep_to_next_day_glucose` - Sleep associated with next-day glucose
- `same_event_as` - Metrics in same event group

### Confidence Calculation
- Use `min(abs(change) / 100, 1.0)` for simple change-based confidence
- Use custom `_spike_confidence()` for meal spikes
- Use `min((threshold - value) / threshold, 1.0)` for severity-based

### Evidence Structure
Always include:
- Primary measured values (carbs, duration, dose)
- Baseline and peak values
- Change amount
- Time delay
- Severity classification

## Verification
- Edge persists to `health_metric_edges`
- Evidence JSON is complete
- Confidence is between 0.0 and 1.0
- Cross-user isolation is maintained
- Failed persistence doesn't crash detection

## Related Skills
- graph-edge-wiring-pattern-detection (this skill)
- graph-provenance-testing
- graph-confidence-testing
- rag-evidence-contract-testing
