# Product Requirements Document: T1D Companion Architecture Consolidation

**Status:** Implemented  
**Date:** 2026-05-30  
**PRD ID:** T1D-ARCH-001

## Executive Summary

This PRD documents the resolution of architectural ambiguity in the T1D Companion project, where two parallel systems (`demo/` and `app/agents/`) created confusion around code ownership, schema definitions, and safety policy enforcement. The solution establishes canonical modules for schemas, a unified safety policy, and clear ownership boundaries.

---

## Problem Statement

### Prior State: Architectural Ambiguity

The T1D Companion codebase had **two parallel systems** that caused confusion and duplication:

| Location | Purpose | Issues |
|----------|---------|--------|
| `demo/` (symlink to `sim_user_insights/demo/`) | Demo runtime with companion pipeline | Intermixed with legacy files, unclear ownership |
| `app/t1d_companion/` | Production companion service | Overlapping functionality, schema duplication |
| `scripts/` | Legacy compatibility layer | Shadow copies of demo files, unclear purpose |

### Specific Pain Points

1. **Schema Duplication**: Multiple incompatible schema definitions for meal forecasts existed in `demo/local_loop.py`, `app/schemas/meal_forecast.py`, and `app/t1d_companion/production/schemas.py`

2. **Safety Policy Scattering**: Safety checks were inline in `LLMService` and duplicated across multiple files. Non-engineer updates required code changes.

3. **Ownership Unclear**: Both `demo/` and `app/t1d_companion/` contained companion pipeline logic, making it unclear which was canonical

4. **Pipeline Runner Complexity**: `run_companion_pipeline` mixed LLM client creation, stage sequencing, and clarification loops in a single function

---

## Solution: Canonical Architecture

### 1. Canonical Schemas (`app/schemas/meal_forecast.py`)

**Decision**: All meal forecasting contracts use the single source of truth at `app/schemas/meal_forecast.py`

```python
# Canonical types exported for all consumers
class MealForecastRequest(BaseModel):  # Input contract
class MealForecastResponse(BaseModel):  # Output contract
class ForecastDetail(BaseModel):
class SafetyInfo(BaseModel):
class NutrientTotals(BaseModel):
# ... plus enums and helpers
```

**Rationale**: Single versioned schema enables forward/backward compatibility across iOS, Flutter, web, and API clients.

### 2. Unified Safety Policy (`data/safety_config.json` + `app/ai/safety.py`)

**Decision**: Externalize all safety configuration to JSON. `SafetyScaffold` class loads config at runtime.

```json
{
  "version": 2,
  "emergency_keywords": {
    "diabetes_emergency": ["severe low", "can't wake", ...],
    "mental_health_crisis": ["kill myself", "suicide", ...],
    "general_medical": ["emergency", "urgent", ...]
  },
  "guardrails": {...},
  "dosing_patterns": [...],
  "treatment_patterns": [...]
}
```

**Rationale**: Non-engineers (MHRA reviewers) can audit and modify safety policy without code changes.

### 3. Clear Ownership Boundaries

| Module | Owner | Purpose | Consumers |
|--------|-------|---------|-----------|
| `demo/` | Demo Team | 12-Factor Agents demo pipeline | Demo runners, scripts shim |
| `app/schemas/` | API Team | Canonical Pydantic contracts | All services, clients |
| `app/food/` | Food Team | Food service, search, schemas | Companion pipelines |
| `app/ai/safety.py` | AI Team | Safety validation scaffold | All LLM stages |
| `scripts/` | Deprecated | Compatibility shim only | Legacy imports |

### 4. FoodSearch Facade (`app/food/search.py`)

**Decision**: Unify lexical and semantic search into `FoodSearch` class with strategy pattern.

```python
class FoodSearch:
    def search(self, food: ParsedFood, limit: int = 5) -> list[Dict]:
        # Merges semantic and lexical results
        # Deduplicates by barcode
        # Returns consistent candidate format
```

**Rationale**: Hides search complexity behind single interface, enables swappable strategies.

### 5. Declarative Pipeline Runner (`demo/runner.py`)

**Decision**: Model pipeline as data-driven stage graph:

```python
class Stage(BaseModel):
    name: str
    needs_llm: bool = False
    needs_db: bool = False

# Stage graph is explicit data structure
_default_stages() = [
    Stage(name="select_profile"),
    Stage(name="parse_foods", needs_llm=True),
    Stage(name="db_lookup", needs_db=True),
    # ...
]
```

**Rationale**: Makes stage ordering visible, supports dependency injection, enables testing without DB/LLM.

---

## Implementation Status

✅ **Complete**: All components implemented and integrated:

- [x] `app/schemas/meal_forecast.py` - Canonical Pydantic schemas (v1.0.0)
- [x] `data/safety_config.json` - Externalized safety configuration (v2)
- [x] `app/ai/safety.py` - `SafetyScaffold` class loads config at runtime
- [x] `app/food/search.py` - `FoodSearch` facade with strategy pattern
- [x] `demo/runner.py` - Declarative `PipelineRunner` with stage graph
- [x] `scripts/README.md` - Documents compatibility shim status
- [x] `demo/README.md` - Documents canonical demo runtime

---

## Migration Guide

### For Consumers Using Legacy Imports

```python
# OLD (deprecated)
from scripts.companion_pipeline_v2 import run_companion_pipeline

# NEW (canonical)
from demo.companion_pipeline_v2 import run_companion_pipeline
```

### For Schema References

```python
# OLD
from app.t1d_companion.production.schemas import CompanionRequest

# NEW
from app.schemas.meal_forecast import MealForecastRequest
```

### For Safety Checks

```python
# OLD (inline in LLMService)
if "take X units" in response:
    # inline check

# NEW
from app.ai.safety import SafetyScaffold
safety = SafetyScaffold()
review = safety.validate(response)
```

---

## Verification Checklist

- [x] All demo pipeline stages use canonical schemas
- [x] `scripts/` files are thin re-exports only
- [x] Safety policy is loaded from JSON, not hardcoded
- [x] Food search returns consistent candidate format with `_semantic_similarity`
- [x] Pipeline runner declares stages as data, not control flow
- [x] Tests pass: `tests/test_meal_forecast_schemas.py`, `tests/test_forecast_safety_validator.py`

---

## Future Considerations

1. **Deprecation of `app/t1d_companion/local_loop.py`**: Food pipeline logic remains for backward compatibility but should migrate to `demo/local_loop.py` patterns

2. **Schema Versioning**: `MealForecastResponse.version` field enables forward compatibility

3. **Alembic Migration**: #183 tracks persistence of meal forecasts for audit trail

---

## References

- Architecture Review: `docs/ARCHITECTURE_REVIEW.md` (4 candidates implemented)
- Refactoring Summary: `REFACTORING_SUMMARY.md` (12-Factor Agents compliance)
- Safety Config: `data/safety_config.json` (MHRA-auditable)
- FoodSearch Facade: `app/food/search.py` (strategy pattern implementation)