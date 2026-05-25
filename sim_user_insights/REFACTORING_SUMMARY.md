# 12-Factor Agents Companion Pipeline Refactoring

## Summary

The companion pipeline has been refactored to follow the [12-Factor Agents](https://github.com/humanlayer/12-factor-agents) principles.

## Changes Made

### 1. Unified State Management (Factor 5)
- Created `CompanionState` dataclass to unify execution and business state
- Enables pause/resume and replayability
- Includes `to_context()` method for context window building

### 2. Explicit Context Window (Factor 3)
- Context is built explicitly via `to_context()` method
- Each stage receives only the context it needs
- No hidden state leakage

### 3. Owned Control Flow (Factor 8)
- Each stage is a pure function: `stage_select_profile()`, `stage_parse_foods()`, `stage_db_lookup()`, `stage_forecast()`, `stage_companion_advice()`
- Stages are composable and testable in isolation
- Pipeline runner `run_companion_pipeline()` sequences stages

### 4. Stateless Reducer (Factor 12)
- Each stage returns a new state (immutable pattern)
- Enables time-travel debugging and replay
- Easy to test: give input state, expect output state

## Files Modified/Created

- `/root/t1d/sim_user_insights/scripts/companion_pipeline_v2.py` - New 12-Factor compliant pipeline
- `/root/t1d/sim_user_insights/scripts/run_structured_companion.py` - Added CompanionState and stage functions

## Usage

```python
from sim_user_insights.scripts.companion_pipeline_v2 import run_companion_pipeline
import asyncio

state = await run_companion_pipeline("chicken burrito bowl", anchor_type="well_controlled")
print(state.response)
```

## Benefits

1. **Testability** - Each stage can be tested independently
2. **Debuggability** - Can inspect state at any point in the pipeline
3. **Replayability** - Save state to disk and resume later
4. **Flexibility** - Easy to swap stages or reorder stages
5. **Safety** - Clear error handling per stage
