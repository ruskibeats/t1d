# State Serialization Spec

Minimum fields for state transfer between CompanionState, CoordinatorContext, and DB records.

## Canonical Serialization

When state crosses boundaries, serialize these fields:

```python
STATE_SERIALIZATION_FIELDS = [
    # Identity
    "scenario",
    "anchor_type",
    
    # Stage outputs (essential)
    "profile_json",      # Profile snapshot (not full config)
    "totals",           # MealSummary: carbs_g, fat_g, sugars_g
    "forecast",         # ForecastResult (with evidence)
    
    # Evidence/Essentials
    "confidence_overall",
    "clarification_needed",
    
    # Meta (for replay/debug)
    "question_mode",
    "safety_rule",
]
```

## Cross-Boundary Rules

- **CompanionState ↔ DB**: Only serialize `STATE_SERIALIZATION_FIELDS`
- **CoordinatorContext**: NOT USED - skip this layer entirely
- **Replay/Resume**: Include full `CompanionState` via `asdict()`

## DB Record Shape

```python
class PredictionRecord(BaseModel):
    scenario: str
    anchor_type: str
    profile_snapshot: dict  # Profile at time of prediction
    meal_totals: dict       # What was predicted
    forecast: dict          # Full forecast with evidence
    evidence: dict          # Evidence fields flattened
    created_at: datetime
```

## Decision

CompanionState is the **single** state carrier. No CoordinatorContext needed or created.