---
name: "run-simulator-pipeline"
description: "Run the synthetic patient simulator pipeline end-to-end: create a SimRun, generate patients from 12 anchor profiles, produce CGM traces, write to production tables, plant hidden truth labels, run PatternService detectors, and evaluate accuracy/precision/recall/F1 with calibration analysis."
version: 3
created: "2026-05-21"
updated: "2026-05-21"
---
# Run the T1D Simulator Pipeline End-to-End

## When to Use

- You need to evaluate PatternService detector accuracy (precision, recall, F1) against known ground truth.
- A new detector was added and needs a benchmark run across all 12 anchor profiles.
- You changed detector parameters or confidence logic and need a regression run.
- You need synthetic patient data (CGM traces, meals, insulin, exercise, sleep) for UI prototyping or integration testing.
- Trigger phrases: "run the simulator", "evaluate detectors", "benchmark pattern service", "simulation run", "generate synthetic data".

**Do NOT use** when you just need a single patient's data for a quick test — use the `scripts/seed_demo_data.py` seeder instead. The simulator is overkill for one-off data generation.

## Procedure

### 1. Understand the Pipeline Architecture

The simulator lives in `app/simulator/` — 12 modules that chain together:

```
anchors.py          → 12 archetype profiles with parameter ranges
patient_factory.py  → samples PatientConfig from an anchor
day_context.py      → generates daily event schedules (meals, insulin, exercise, sleep)
glucose_engine.py   → physiological CGM trace at 5-min intervals (circadian, meal, insulin, exercise, noise)
writeback.py        → writes synthetic data into production tables (health_metrics + legacy)
truth_labels.py     → plants hidden ground-truth labels in sim_hidden_truths
evaluator.py        → matches PatternService edges to truths, computes precision/recall/F1
calibration.py      → binned calibration curves, ECE (Expected Calibration Error), threshold recommendations
service.py          → orchestrator: creates SimRun → generates all patients → writes → detects → evaluates
models.py           → SQLAlchemy ORM: SimRun, SimUser, SimHiddenTruth, SimDetectorScore
schemas.py          → Pydantic models: AnchorType enum (12 values), PatientConfig, RunStatus, etc.
```

**Critical constraint**: `sim_hidden_truths` must NEVER be accessible through user-facing RAG context, graph queries, or chat endpoints. Truth labels are the evaluation reference — exposing them would invalidate all benchmark results.

### 2. Set Up the Environment

```bash
# Ensure database is up and migrations applied
cd /root/t1d
alembic upgrade head

# Check that pattern_service imports work
python3 -c "from app.services.pattern_service import PatternService; print('OK')"

# Verify simulator imports
python3 -c "from app.simulator.service import SimulationService; print('OK')"
```

If migrations fail, check `app/db/base.py` for uncovered `__import__` or delayed model imports — the simulator models live in `app/simulator/models.py` and must be registered with the metadata before migration.

### 3. Create a Simulation Run

Via the FastAPI endpoint or directly in code:

**Option A — API** (when the server is running):
```bash
curl -X POST http://localhost:8000/api/v1/simulator/runs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "baseline-v2-detectors",
    "description": "Benchmark run for exercise + delayed fat detectors",
    "anchor_count": 12,
    "users_per_anchor": 20,
    "days_per_user": 90
  }'
```

**Option B — Python** (for scripted or CI use):
```python
from app.simulator.schemas import SimRunCreate, AnchorType
from app.simulator.service import SimulationService

service = SimulationService(db)
run = await service.create_run(
    SimRunCreate(
        name="quick-validation",
        description="5 anchors, 3 users each, 30 days — fast check",
        anchor_count=5,       # fewer anchors for speed
        users_per_anchor=3,   # fewer patients per anchor
        days_per_user=30,     # shorter simulation period
    )
)
```

### 4. Start the Run (Generate + Evaluate)

```python
# This single call orchestrates the full pipeline:
result = await service.start_run(run.id)

# Runoutput is the SimRun with status and summary_json populated
print(f"Detection rate: {result.summary_json['detection_rate']}")
```

`start_run` executes these steps in order:

1. **Creates SimRun record** — status → `generating`
2. **For each anchor type** (1–12, ordered by `users_per_anchor`):
   a. Generate `PatientConfig` instances from anchor parameter ranges (uniform sampling)
   b. For each patient:
      - Generate daily event schedules via `DayContextGenerator` (90 days × event types)
      - Run `GlucoseEngine` → 5-min interval CGM trace (~25,920 readings over 90 days)
      - **Write via SimulatorWriteback** — legacy tables (glucose + events) then health_metrics
      - Create `SimUser` record linking real_user_id to the simulated identity
      - **Plant truth labels** via `TruthLabelPlacer` (post_meal_spike, overnight_low, exercise_effect, delayed_high_fat)
3. **Run PatternService detectors** — calls `detect_post_meal_spikes`, `detect_overnight_hypoglycemia`, `analyze_exercise_impact`, `detect_delayed_high_fat_effects` on each user's data
4. **Run evaluation** — `SimulatorEvaluator` matches detector edges to hidden truths, computes precision/recall/F1 by anchor and pattern type
5. **Run calibration analysis** — binned ECE, per-pattern calibration curves, confidence threshold recommendations
6. **Stores everything** — scores in `sim_detector_scores`, summary in `sim_run.summary_json`, status → `completed`

**Pitfall**: Large runs (12 anchors × 20 users × 90 days = 2.4M+ metric rows) can take 10–15 minutes. Monitor DB connection timeouts and consider increasing pool_pre_ping settings.

### 5. Read Results

**Via API**:
```bash
# Get run summary
curl http://localhost:8000/api/v1/simulator/runs/1

# Get truths (planted + detection status)
curl http://localhost:8000/api/v1/simulator/runs/1/truths

# Get detector scores
curl http://localhost:8000/api/v1/simulator/runs/1/scores
```

**Direct DB queries**:
```python
# Get run
run = await service.get_run(run_id)

# Get summary metrics
metrics = run.summary_json
print(f"Detection rate: {metrics['detection_rate']}")
print(f"Avg confidence: {metrics['avg_confidence_detected']}")

# Per-pattern breakdown
for pattern, m in metrics['by_pattern_type'].items():
    print(f"{pattern}: precision={m['precision']} recall={m['recall']} f1={m['f1']}")

# Calibration ECE
cal = metrics.get('calibration', {})
print(f"Overall ECE: {cal.get('ece_summary', {}).get('overall_ece')}")
```

### 6. Interpret Calibration Results

The calibration analysis (`app/simulator/calibration.py`) answers:
- **ECE (Expected Calibration Error)**: ≤0.05 is well-calibrated, ≥0.15 needs attention
- **Threshold recommendations**: Minimum confidence to achieve 80% accuracy (deployment target)
- **Per-bin charts**: Each bin shows (avg_confidence, empirical_accuracy) — diagonal = perfect calibration

```python
cal = run.summary_json.get('calibration', {})
thresholds = cal.get('threshold_recommendations', [])
for t in thresholds:
    print(f"{t['detector']}: min conf={t['min_confidence']} → {t['expected_accuracy']*100:.0f}% accuracy")
```

### 7. Adding New Anchor Profiles

To extend the 12 anchor profiles:

1. Add a new enum value to `AnchorType` in `app/simulator/schemas.py`
2. Add parameter ranges in `app/simulator/anchors.py` (`ANCHOR_PARAMETER_RANGES` dict)
3. Add label and description in `anchor_label()` and `anchor_description()` helpers
4. If the anchor should have different event generation logic, extend `DayContextGenerator` in `app/simulator/day_context.py`

### 8. Adding New Pattern Detection Types

To evaluate a new detector:

1. Add the new pattern type to `TruthLabelPlacer` (e.g., `plant_new_pattern_truths()`) in `app/simulator/truth_labels.py`
2. Call it from `plant_all_truths()` in the same file
3. Add the edge type mapping in `SimulatorEvaluator.TRUTH_TO_EDGE_TYPE` in `app/simulator/evaluator.py`
4. Call the new PatternService detector in `SimulationService._run_detectors()` in `app/simulator/service.py`

## Pitfalls
### Data isolation violations
- **`sim_hidden_truths` must NEVER appear in user-facing RAG context, graph queries, or chat endpoints.** These are internal ground-truth labels. If a query joins across `sim_` tables, apply a strict filter to exclude them from user-facing flows.
- Always tag synthetic data with `source="simulator"` and embed `sim_run_id` + `sim_user_key` in `meta` for traceability. The `SimulatorWriteback` class does this automatically.
- **Sim users in `tbl_users`** have email pattern `sim_<sim_user_key>@simulator.local` and `hashed_password="SIMULATOR_USER_NO_LOGIN"`. Any user-facing user list or auth flow must filter these out — e.g., `WHERE email NOT LIKE 'sim_%@simulator.local'`.

### Detector failures are non-fatal per patient
- `_run_detectors` catches exceptions per user and logs a warning: `"Detector run failed for user {user_id}"`. A single detector failure (e.g., missing edges for a specific user) yields `false_negatives` for that user's truths but does not fail the entire run. Always check the logs after a run.

### Truth-to-edge matching timezone issues
- `SimHiddenTruth.window_start`/`window_end` are naive datetimes (no tzinfo). `HealthMetric.measured_at` may be timezone-aware. The evaluator handles this with `replace(tzinfo=timezone.utc)`, but if you add custom matching logic in `_match_truth_to_edge`, watch for timezone mismatches — comparisons between aware and naive datetimes raise `TypeError`.
- Match tolerance is `MATCH_TOLERANCE_MINUTES = 30` in `evaluator.py`. Adjust for stricter/looser matching.

### Batch commit hygiene
- Writing CGM data for 30+ days × ~288 readings/day = ~8640 readings/patient. For 100+ patients that's ~864k health_metrics rows. The writeback chunks at 500 per batch. Ensure `await db.flush()` is called periodically — the service does this every 10 patients to avoid OOM in the SQLAlchemy session identity map.
- Legacy table writes (`tbl_glucose_readings`, `tbl_context_events`) flush every 500 rows. If you add new legacy tables, match this chunking pattern.

### Large runs can take hours, not minutes
- 12 anchors × 20 users × 90 days = 21,600 patient-days. At ~1 second per patient for the full pipeline, that's ~6 hours. Start small (2-3 anchors, 5 users, 7 days) for iteration.
- The DB connection may time out during long runs. Set `pool_recycle=3600` and `connect_args={'options': '-c statement_timeout=300000'}` for the simulator session.

### Calibration edge cases
- Calibration analysis (`compute_full_calibration_summary`) requires truth records with populated `detector_confidence`. If no truths were detected (all false negatives), calibration results will be empty — this is normal.
- If a detector always returns confidence ≥0.9, bins below 0.9 will be empty. `find_threshold()` handles this by scanning from highest confidence down, but empty bins make ECE less informative.

### Seed reproducibility
- Each patient's seed is derived from `run.id * 10000 + user_index * 100`. If you change anchor processing order (e.g., alphabetically vs. by `AnchorType` enum order), all seeds change and results won't be comparable across runs.
- To reproduce a specific patient, note `SimUser.seed` and reconstruct the `PatientConfig` directly via `generate_patient_config(anchor_type, seed=...)`.

### Detector versioning
- `SimDetectorScore.detector_version` is hardcoded as `"1.0"` in the evaluator's `_store_scores()`. Bump this when detector algorithms change so score comparisons across run versions are valid.
## Verification
- **Run created**: `GET /api/v1/simulator/runs/{id}` returns `"status": "completed"` and `summary_json` populated with metrics.
- **Detection rate > 0**: `summary_json.detection_rate` should be > 0 (typically 0.6–0.95 for good detectors). If 0.0, check that `TRUTH_TO_EDGE_TYPE` in `evaluator.py` has the correct edge type mappings for your pattern types.
- **Truths planted**: `GET /api/v1/simulator/runs/{id}/truths` returns rows with `is_detected` populated (not None). If 0 rows, check truth placer thresholds (`MIN_SPIKE_CARBS`, etc.) against simulated glucose values.
- **Calibration computed**: `summary_json.calibration.ece_summary.overall_ece` is a float, not None or an error string.
- **Scores stored**: `GET /api/v1/simulator/runs/{id}/scores` returns rows for `overall_precision`, `overall_recall`, `overall_f1` and per-pattern metrics.
- **Legacy tables populated**: `SELECT COUNT(*) FROM tbl_glucose_readings WHERE source='simulator'` returns > 0.
- **No synthetic user leakage**: Verify `tbl_users.email LIKE 'sim_%@simulator.local'` users are excluded from user-facing queries, auth flows, and chat RAG context. A passing check: `SELECT * FROM user_facing_view LIMIT 5` shows no `sim_` emails.
- **No truth leakage**: Search for `sim_hidden_truths` joins in user-facing code paths (chat RAG, graph queries, API endpoints) — should not appear outside the `app/simulator/` package. Run `grep -rn 'sim_hidden_truths' app/ --include='*.py' | grep -v simulator/` to confirm zero results outside the simulator package.