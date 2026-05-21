# Plan: [ARCH-DATA] Sprint 15: Health Metrics Registry

## Intended Outcome
Create a centralized **Metric Registry** for the dual-write architecture:
1. Map domain events to `MetricType` enums centrally
2. Handle dual-write through a single seam
3. Register graph edge detectors alongside metric types

## Step-by-Step

### Phase 1: Metric Registry Core (S15-D1)
1. Create `app/metrics/registry.py` with MetricRegistry class
2. Define `MetricMapping` dataclass with domain_type, metric_type, edge_detectors
3. Register all existing domain mappings (glucose, meal, exercise, sleep, insulin)
4. Add `write_if_present()` method for dual-write handling
5. Write tests in `tests/test_metric_registry.py`

### Phase 2: Domain Table Integration (S15-D2)
1. Update FoodService to use MetricRegistry instead of direct calls
2. Update ExerciseService to use MetricRegistry
3. Update SleepService to use MetricRegistry
4. Update FastingService to use MetricRegistry
5. Verify all 16 domains write to health_metrics correctly

### Phase 3: Graph Edge Registration (S15-D3)
1. Extend MetricRegistry to accept edge_detector callables
2. Register meal→spike detector for CARBS metric
3. Register exercise→drop detector for EXERCISE_MINUTES
4. Register sleep→glucose detector for SLEEP_HOURS
5. Add integration tests in `tests/test_registry_edges.py`

## Files
- `app/services/metric_writer.py` - Centralize
- `app/food/service.py` - Update imports
- `app/exercise/service.py` - Update imports
- `app/sleep/service.py` - Update imports
- `app/fasting/service.py` - Update imports
- `16 domain service files` - Update to use registry

## Verification
```bash
pytest tests/test_metric_registry.py -v
pytest tests/test_registry_edges.py -v
alembic check  # Verify migrations still valid
python -c "from app.metrics.registry import registry; print('OK')"
```

## Skills Required
- `improve-codebase-architecture` - Centralize dual-write logic
- `tdd` - Test registry behavior

## Audit
### Files Changed
- `app/metrics/registry.py` (new)
- `app/services/metric_writer.py` (consolidate/update)
- 16+ domain service files (update)
- `tests/test_metric_registry.py` (new)
- `tests/test_registry_edges.py` (new)

### Token Burn Estimate
~20,000 tokens (registry), ~15,000 tokens (domain updates), ~10,000 tokens (edge registration)

### Blockers/Follow-ups
Depends on existing health_metrics table structure remaining stable.