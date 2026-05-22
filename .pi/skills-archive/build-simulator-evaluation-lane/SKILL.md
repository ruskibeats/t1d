---
name: "build-simulator-evaluation-lane"
description: "Build a glucose simulation + pattern-detector evaluation lane for the T1D Companion. Creates anchored patient profiles, physiological glucose engine, hidden-truth labels, writeback to production tables, and an evaluator (precision/recall/F1 + calibration ECE)."
version: 6
created: "2026-05-21"
updated: "2026-05-21"
---
# Build Simulator + Evaluation Lane

## When to Use
Add simulation-driven evaluation of the `PatternService` detectors against ground-truth synthetic data. Use when you need to quantitatively measure detector precision/recall/F1, calibrate confidence thresholds, or verify that new detector logic improves detection without regressing existing patterns.

## Architecture

```
Simulator Layer
├── anchors.py              # Patient anchor profiles (adolescent, athlete, dawn phenomenon, etc.)
├── patient_factory.py      # Deterministic patient config generation from anchors
├── day_context.py          # Daily meal/exercise/insulin event generation
├── glucose_engine.py       # Physiological model: basal + meal rise + insulin decay + exercise dip
├── truth_labels.py         # Hidden truth planting (what patterns should be detectable)
├── writeback.py            # Writes synthetic data into health_metrics + legacy tables
│
Evaluation Layer
├── evaluator.py            # Matches detector edges to hidden truths -> precision/recall/F1
├── calibration.py          # Binned accuracy, ECE, reliability metrics, threshold recommendations
│
Orchestration
├── service.py              # SimulatorService: run -> orchestrate generation + writeback + detect + evaluate
├── models.py               # SQLAlchemy ORM: SimRun, SimUser, SimHiddenTruth, SimDetectorScore
├── schemas.py              # Pydantic schemas for API
    
Integration
├── api/simulator.py        # FastAPI endpoints: trigger run, get results, get calibration
└── alembic/versions/       # Migration for simulator tables
```

## Step 1 — Create Alembic Migration

```python
# alembic/versions/add_simulator_tables.py
"""
Create simulator tables:
- sim_runs: tracks each orchestrated run
- sim_users: links sim users to real users + anchor profiles
- sim_hidden_truths: planted ground-truth labels
- sim_detector_scores: evaluator/calibration results
"""

revision = "add_simulator_tables"
down_revision = "add_event_group_id_to_health_metrics"  # current head
```

Key columns:
- `sim_runs`: id (UUID), config_json, status (created/running/completed/failed), created_at, completed_at
- `sim_users`: id, sim_run_id (FK), real_user_id (nullable FK), anchor_type (str), config_json
- `sim_hidden_truths`: id, sim_run_id (FK), sim_user_id (FK), pattern_type (str), window_start/end, details_json, is_detected (bool)
- `sim_detector_scores`: id, sim_run_id (FK), sim_user_id (nullable FK), detector_name/version, anchor_type (nullable), pattern_type (nullable), metric_name, metric_value (float), breakdown_json

## Step 2 — Simulator Models (SQLAlchemy)

Create `app/simulator/models.py` with ORM classes mirroring the migration. Import at bottom of `app/db/models.py` to register with `Base.metadata`:

```python
# In app/db/models.py
from app.simulator.models import *  # noqa: F401, F403
```

## Step 3 — Anchors + Patient Factory

**anchors.py**: Define ~10 patient anchor profiles with realistic metabolic parameters:
- `BASAL_RATE` (basal insulin mg/dL per min)
- `MEAL_RISE_FACTOR` (how aggressively carbs spike glucose)
- `INSULIN_SENSITIVITY`, `EXERCISE_DROP_RATE`, `DAWN_EFFECT_STRENGTH`
- `BODY_WEIGHT` (kg) for distribution volume
- `ACTIVITY_LEVEL` (sedentary/active/athlete)

Anchor profiles (examples):
- `adolescent_high_variance`: Higher basal, strong meal spike, unpredictable overnight
- `dawn_phenomenon`: Pronounced morning rise (peaks at 5-7am)
- `athlete_low_var`: Higher exercise sensitivity, tight control
- `brittle_t1d_low_control`: High variance, low TIR
- `senior_hypo_unaware`: Frequent asymptomatic lows

**patient_factory.py**: `generate_config(anchor, rng, user_id_offset)` — parse anchor params, apply jitter (5-15% variation via seed RNG). Deterministic for reproducibility.

## Step 4 — Day Context Generator

**day_context.py**: Generate one day of lifestyle events for a patient config:
- Meals: 3 meals + 1-3 snacks with randomized time/carbs/fat
- Insulin: bolus doses tied to meals + corrections + missed doses
- Exercise: 1-2 sessions per day

Return `DayContext` dataclass with lists of `MealEvent`, `InsulinEvent`, `ExerciseEvent`.

**Pitfall**: Random hour generation — `randint(22, 24)` returns 24 which is invalid. Use `randint(22, 23)` for 10pm-11pm bounds.

## Step 5 — Glucose Engine

**glucose_engine.py**: Physiological model producing 5-min CGM readings:

```python
def simulate_day_glucose(config, day_context, rng):
    readings = []
    bg = config.get("fasting_glucose", 120.0)
    for minute in range(0, 1440, 5):
        # Dawn effect: linear rise from 3am-7am, capped
        if 180 <= minute < 420:
            bg += dawn_rise_per_min * 5
        
        # Basal insulin: gradual decrease
        bg -= bg * basal_rate * 5
        
        # Meal absorption: gaussian-like rise peaking ~30-45min post-meal
        for meal in active_meals:
            bg += carb_increase(meal, minute)
        
        # Exercise: linear drop during and 30min post
        for ex in active_exercises:
            if ex.active(minute):
                bg -= ex_drop_per_min * 5
        
        # Recovery drift toward baseline
        bg += (target_bg - bg) * recovery_rate * 5
        
        # Sensor noise: +/- 5% gaussian
        bg += rng.gauss(0, bg * 0.05)
        
        readings.append((minute + day_offset, bg))
    return readings
```

**Pitfall**: Ensure CGM readings are spaced exactly 5 minutes apart. Cache active meals/exercises per minute for performance.

## Step 6 — Truth Labels

**truth_labels.py**: Plant hidden truths that represent known pattern types:
- `post_meal_spike`: Check if glucose > 180 within 2h of a meal with >30g carbs
- `overnight_low`: Check if glucose < 70 between midnight and 6am
- `dawn_phenomenon`: Check if glucose rises >30% between 3am-7am
- `exercise_effect`: Check if glucose drops >20% within 1h of exercise

```python
def plant_truths(config, day_context, cgm_readings, sim_run_id, sim_user_id):
    truths = []
    for meal in day_context.meals:
        peak = max(g for t, g in cgm_readings if meal.time <= t < meal.time + 120)
        if peak > 180 and meal.carbs > 30:
            truths.append(SimHiddenTruth(
                pattern_type="post_meal_spike",
                window_start=meal.time, window_end=meal.time + 120,
                details_json={"meal_carbs": meal.carbs, "peak_glucose": peak}
            ))
    return truths
```

**Pitfall**: Increase carb quantities in test fixtures (e.g., 120g carbs, not 15g) to reliably produce spikes >180 mg/dL for verification tests.

## Step 7 — Writeback

**writeback.py**: Write synthetic data into production tables:

1. **Patient setup**: Create real `User` rows for each sim user
2. **Health metrics**: Batch-write glucose readings as `HealthMetric` rows with `MetricType.BLOOD_GLUCOSE` and `unit="mg/dL"`. Use `app.metrics.service.HealthMetricService.create_batch()`
3. **Legacy events**: Optionally write `ContextEvent` rows for meals, insulin, exercise
4. **Register sim user**: Create `SimUser` linking sim_user_id → real_user_id → anchor_type

**Pitfalls**:
- `create_batch()` expects `BatchHealthMetricCreate(metrics=[...])` wrapper, not a raw list — wrap it
- Batch size limit is 1000 — **chunk** into slices of 500
- 1440/5 = 288 CGM readings per day × users = potentially hundreds of metrics. Always chunk.

## Step 8 — Evaluator

**evaluator.py**: Match PatternService's detected `HealthMetricEdge` results against hidden truths:

```python
class SimulatorEvaluator:
    TRUTH_TO_EDGE_TYPE = {
        "post_meal_spike": ["meal_to_glucose_spike", "meal_to_delayed_spike"],
        "overnight_low": ["overnight_low"],
        "exercise_effect": ["exercise_to_glucose_drop"],
        "dawn_phenomenon": ["dawn_phenomenon"],
        "delayed_high_fat": ["meal_to_delayed_spike"],
    }
    
    def match_edge_to_truth(self, truth, edges):
        """Find a detected edge that matches this hidden truth."""
        expected_types = self.TRUTH_TO_EDGE_TYPE[truth.pattern_type]
        for edge in edges:
            if str(edge.edge_type) not in expected_types:
                continue
            source_time = self._get_edge_source_time(edge)
            if source_time and truth.window_start <= source_time <= truth.window_end:
                return edge
        return None
    
    def _get_edge_source_time(self, edge):
        """Use source_metric.timestamp, NOT edge.created_at."""
        if hasattr(edge, 'source_metric') and edge.source_metric and hasattr(edge.source_metric, 'timestamp'):
            return edge.source_metric.timestamp
        return None
```

**Key insight**: Use `source_metric.timestamp` (the actual metric time) not `edge.created_at` (database row time) for temporal window matching.

Computes: TP/FP/FN, precision, recall, F1 per pattern type + anchor type. Stores in `sim_detector_scores`.

## Step 9 — Calibration Module

**calibration.py**: Binned accuracy, ECE, and threshold recommendations:

```python
def compute_calibration_metrics(predictions):
    """
    Args:
        predictions: List of (confidence: float, is_correct: bool)
    
    Returns:
        dict with bins, ECE, MCE, threshold recommendations
    """
    bins = [0.0] * 10  # 0-0.1, 0.1-0.2, ..., 0.9-1.0
    for conf, correct in predictions:
        bin_idx = min(int(conf * 10), 9)
        bins[bin_idx].append((conf, correct))
    
    ece = 0.0
    for bin_idx, items in enumerate(bins):
        if not items:
            continue
        bin_accuracy = sum(c for _, c in items) / len(items)
        avg_confidence = sum(c for c, _ in items) / len(items)
        bin_center = (bin_idx + 0.5) / 10
        ece += (len(items) / total) * abs(bin_accuracy - avg_confidence)
    
    return {"ece": ece, "mce": mce, "bins": bin_summaries, "thresholds": threshold_recs}
```

**v1**: Non-Bayesian binning. **v1.1**: Bayesian binning with beta prior (adds confidence interval around each bin accuracy). **v1.2**: Pool-adjacent-violators isotonic regression (PAV) for smoothed calibration curve.

**Code review finding — sparse bin protection**: Sparse bins (low sample count) produce unreliable ECE estimates. Protect against them:
- Set `MIN_SAMPLES_PER_BIN = 5` — if a bin has fewer samples, it's too unreliable to report independently
- **Auto-merge sparse bins** into the nearest populated neighbor: scan left-to-right, merge any bin with `support < min_samples` into the previous or next populated bin (whichever is closer in confidence space)
- Report `merged_indices` in `to_dict()` so consumers know which bins were collapsed
- This avoids misleading calibration curves where a bin with 1 sample shows 100% accuracy

**Code review finding — min_samples floor for threshold**: `find_threshold()` should require a minimum sample count *above the candidate threshold* before issuing a recommendation:
- Add `min_samples` parameter (default 10) to `find_threshold_confidence()`
- The running accuracy accumulator must see at least `min_samples` predictions above the candidate confidence before considering it valid
- Without this floor, a single high-confidence correct prediction would produce `min_confidence = 0.99` on 1 sample — a dangerously overconfident recommendation

**v2 TODO — learned scoring path**: Confidence is currently edge-weight-only. For v2, replace heuristic confidence with a learned model:
```python
# logistic_regression([delta_peak, time_to_peak_min, auc_above, baseline_variance])
# Requires ~240 users × 90 days of labeled edges from simulator runs
# One binary classifier per pattern type
```

## Step 10 — Orchestrator Service

**service.py**: `SimulatorService.run()`:
1. Create `SimRun` with config JSON
2. Generate patient configs from anchors
3. For each user × day:
   - Generate day context
   - Run glucose engine
   - Plant hidden truths
   - Write to database
4. Run PatternService detectors
5. Run evaluator + calibration
6. Mark run as completed

## Step 11 — API Endpoints

**api/simulator.py**: FastAPI router:
- `POST /api/v1/simulator/runs` — Create a run (body: anchor_count, users_per_anchor, days_per_user)
- `POST /api/v1/simulator/runs/{run_id}/start` — Start (trigger) a run
- `GET /api/v1/simulator/runs` — List runs with status and scores
- `GET /api/v1/simulator/runs/{run_id}` — Detailed results with calibration
- `DELETE /api/v1/simulator/runs/{run_id}` — Clean up a run

**CRITICAL: All routes must be auth-gated, including GET routes.** Apply `require_active_user` as a FastAPI dependency on every endpoint — both mutating and read-only routes. Simulator data is internal and should never be accessible without authentication:

```python
@router.get("/runs", response_model=list[SimRunResponse], summary="List simulation runs")
async def list_runs(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),  # <-- MUST include on GET routes too
) -> ...:
```

Every route in the router should either use `include_router(..., dependencies=[Depends(require_active_user)])` at the router level, or each route function should have the `current_user: User = Depends(require_active_user)` parameter. The `Depends(require_active_user)` calls `requires_active_user` which returns the authenticated user — assign it to a parameter even if unused.

Wire into `app/main.py`:

```python
# In create_app()
from app.api.simulator import router as simulator_router
app.include_router(simulator_router, prefix="/api/v1")
```

## Step 12 — Tests

Create one test file per layer:
- `tests/test_simulator_generation.py` — Anchors, patient factory, day context, glucose engine
- `tests/test_simulator_writeback.py` — Writeback mocks (use regular `Mock` not `AsyncMock` for `db.add`)
- `tests/test_simulator_truth_labels.py` — Truth planting logic
- `tests/test_simulator_evaluator.py` — Edge matching, precision/recall
- `tests/test_pattern_service_simulator.py` — End-to-end integration

**Pitfall**: In async test context, use `Mock` not `AsyncMock` for `db.add()` sync methods, otherwise you'll get RuntimeWarning about unawaited coroutines.

## Verification

```bash
# Unit tests (no DB)
python3 -m pytest tests/test_simulator_generation.py -v

# Writeback tests (with mock session)
python3 -m pytest tests/test_simulator_writeback.py -v

# Truth labels and evaluator
python3 -m pytest tests/test_simulator_truth_labels.py -v
python3 -m pytest tests/test_simulator_evaluator.py -v

# End-to-end (with SQLite in-memory)
python3 -m pytest tests/test_pattern_service_simulator.py -v

# Full suite — no regressions
python3 -m pytest tests/test_simulator_*.py tests/test_pattern_service_simulator.py -v

# Existing tests — no regressions
python3 -m pytest tests/test_pattern_service.py tests/test_graph_confidence.py -v
```

Expected results:
- All generation tests pass (anchors, factory, context, glucose, truth labels)
- Evaluator: match_post_meal_spike_truth, no_match_when_no_edges, no_match_wrong_type, highest_confidence_selected, test_match_success all pass
- End-to-end: pattern service detects edges from simulated data, evaluator produces scores
- Zero regressions in existing pattern tests
