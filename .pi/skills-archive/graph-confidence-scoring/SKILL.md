---
name: graph-confidence-scoring
description: Implement transparent confidence scoring for graph edges using decomposed components with weighted aggregation, threshold categorization, and provenance tracking.
---

# Graph Confidence Scoring

## Purpose
Implement confidence scoring for graph edges using decomposed components with weighted aggregation. This provides transparent, explainable confidence scores for observational relationships between health metrics.

## When to Use
When adding or modifying pattern detection methods that persist graph edges, and you need transparent confidence scoring.

## Procedure

### 1. Define ConfidenceComponents
```python
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

@dataclass
class ConfidenceComponents:
    """Decomposed confidence components for graph edge scoring."""
    pattern_strength: float  # How strong is the pattern match (0-1)
    temporal_alignment: float  # Time window match quality (0-1)
    effect_magnitude: float  # Size of the effect (0-1)
    data_quality: float  # Completeness of data (0-1)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_strength": self.pattern_strength,
            "temporal_alignment": self.temporal_alignment,
            "effect_magnitude": self.effect_magnitude,
            "data_quality": self.data_quality,
        }
    
    def combined_score(self) -> float:
        """Calculate combined confidence score with weights."""
        return (
            self.pattern_strength * 0.4 +
            self.temporal_alignment * 0.3 +
            self.effect_magnitude * 0.2 +
            self.data_quality * 0.1
        )
```

### 2. Define ConfidenceThresholds
```python
@dataclass
class ConfidenceThresholds:
    """Confidence thresholds for UI/RAG wording."""
    LOW: float = 0.3
    MEDIUM: float = 0.6
    HIGH: float = 0.8

def categorize_confidence(confidence: float) -> str:
    """Return 'low', 'medium', or 'high' for a confidence score."""
    if confidence < ConfidenceThresholds.MEDIUM:
        return "low"
    elif confidence < ConfidenceThresholds.HIGH:
        return "medium"
    return "high"
```

### 3. Build Provenance
```python
def build_provenance(
    detector_name: str,
    detector_version: str,
    components: ConfidenceComponents,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build provenance payload for graph edge."""
    provenance = {
        "detector": detector_name,
        "detector_version": detector_version,
        "scoring": {
            "method": "weighted_sum",
            "components": components.to_dict(),
        },
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
    if extras:
        provenance.update(extras)
    return provenance
```

### 4. Calculate Confidence in Detection Methods
```python
def _spike_confidence(self, glucose_rise: float, peak_value: float) -> float:
    """Score confidence for a meal-to-spike edge."""
    rise_component = min(max((glucose_rise - 50) / 100, 0), 1)
    peak_component = min(max((peak_value - self.HYPER_THRESHOLD) / 100, 0), 1)
    return round(0.5 + (rise_component * 0.3) + (peak_component * 0.2), 2)
```

### 5. Persist with ConfidenceComponents
```python
components = ConfidenceComponents(
    pattern_strength=0.9,
    temporal_alignment=0.8,
    effect_magnitude=0.7,
    data_quality=0.9,
)

edge = await HealthGraphService(session).upsert_edge(
    user_id,
    HealthMetricEdgeCreate(
        source_metric_id=source.id,
        target_metric_id=target.id,
        edge_type=GraphEdgeType.MEAL_TO_GLUCOSE_SPIKE,
        confidence=components.combined_score(),
        algorithm="pattern_service.post_meal_spike.v1",
        evidence={"components": components.to_dict()},
        confidence_components=components.to_dict(),
        provenance=build_provenance("pattern_service", "1.0.0", components),
    ),
)
```

## Key Patterns

### Weight Formula
- pattern_strength: 0.4 (most important - how well the pattern matches)
- temporal_alignment: 0.3 (time window quality)
- effect_magnitude: 0.2 (size of observed effect)
- data_quality: 0.1 (completeness of supporting data)

### Simple Confidence Calculation
For simple change-based confidence:
```python
confidence = min(abs(change) / 100, 1.0)
```

### Severity-Based Confidence
```python
confidence = min((threshold - value) / threshold, 1.0)
```

## Testing

### Test confidence components JSON
```python
@pytest.mark.asyncio
async def test_confidence_components_json(db_session, test_user):
    """Test confidence_components JSON structure on edges."""
    components = ConfidenceComponents(
        pattern_strength=0.9,
        temporal_alignment=0.8,
        effect_magnitude=0.7,
        data_quality=0.9,
    )
    edge = await service.upsert_edge(
        user_id, HealthMetricEdgeCreate(
            ...
            confidence=components.combined_score(),
            confidence_components=components.to_dict(),
        ),
    )
    assert edge.confidence_components["pattern_strength"] == 0.9
```

### Test confidence threshold language
```python
assert categorize_confidence(0.5) == "low"
assert categorize_confidence(0.7) == "medium"
assert categorize_confidence(0.9) == "high"
```

### Test overall confidence calculation
```python
components = ConfidenceComponents(...)
expected = (0.8 * 0.4 + 0.7 * 0.3 + 0.6 * 0.2 + 0.9 * 0.1)
assert abs(components.combined_score() - expected) < 0.01
```

## Pitfalls
- Verify weight formula matches implementation
- Test edge cases (all low confidence, all high confidence)
- Ensure confidence_components JSON round-trips correctly
- Check that upsert_edge preserves confidence_components
- Use TypeBox StringEnum carefully - empty string causes Gemini API rejection

## Verification
- All confidence tests pass
- Component values match expected calculations
- Threshold language mapping is correct
- Combined scores are within acceptable tolerance
- Edge persistence includes confidence_components

## Related Skills
- graph-edge-wiring-pattern-detection
- graph-provenance-testing
- graph-confidence-testing
- rag-evidence-contract-testing
