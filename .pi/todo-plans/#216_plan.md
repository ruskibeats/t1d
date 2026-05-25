# Clanker Ops #216: Run validation cohort script to verify glucose trace improvements

## Intended Outcome
Obtain rigorous quantitative evidence that simulator calibration succeeded in producing clinically plausible, distinguishable glucose traces for all 12 anchor types. Verify that:
1. Detectors can find patterns in the simulated data (health_metric_edges > 0)
2. Detection rates are meaningful (>0% and improving from baseline)
3. Glucose traces stay within clinically reasonable bounds
4. Meal spikes are detectable but not extreme
5. No anchor shows degenerative behavior (flatlines, excessive volatility)

## Files to Run
- `scripts/validate_cohort_168.py` - Creates 5-patient, 7-day simulation and runs detection/evaluation
- Optional: `python -m pytest tests/test_simulator_* -x` to ensure no regressions

## Key Improvements Over Basic Run
This plan adds specific verification checkpoints and success criteria beyond just running the script.

## Detailed Verification Procedure

### Pre-Run Checks
1. Confirm baseline state:
   ```bash
   # Check no stray edges from previous runs
   psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM health_metric_edges;" || echo "DB check failed"
   # Should show 0 or very low count
   ```

2. Verify simulator still passes unit tests:
   ```bash
   python -m pytest tests/test_simulator_generation.py tests/test_simulator_calibration.py -x --tb=short
   # Must pass
   ```

### Execution
Run the validation with timing and full output capture:
```bash
time python scripts/validate_cohort_168.py 2>&1 | tee validation_output.log
```

### Post-Run Analysis Checklist
Examine the validation output for these specific indicators:

#### ✅ REQUIRED (Must Pass)
- [ ] **health_metric_edges > 0** - Detectors must be finding patterns
  - Look for line: `health_metric_edges: X (+Y new)` where X > 0
- [ ] **No increase in ceiling hits** - No anchor should show >5% ceiling
  - Check SQL EVIDENCE section for per-anchor ceiling %
  - All should be ≤2% (allowing small random variation)
- [ ] **Validation completes successfully** - Must see "✅ Run completed successfully"
- [ ] **All 180+ simulator tests still pass** - Run quick regression check

#### 🎯 TARGET METRICS (Should Show Improvement)
- [ ] **Detection rate > 0%** - Must improve from historical 0%
  - Look for: `Detection rate: X%` where X > 0
- [ ] **Meaningful truths detected** - Some truths should be matched
  - Look for: `truths_detected: X` where X > 0 (ideally >20% of total)
- [ ] **Reasonable F1 scores** - At least some patterns should be detectable
  - Check `by_pattern_type` for F1 > 0.1 on major patterns
- [ ] **Stable glucose ranges** - No anchor should exceed physiological bounds
  - Check that max glucose < 400 for all anchors (our engine caps at 395)
  - Check that min glucose > 40 (extremely low but not impossible)

#### 🔍 DETAILED PERFORMANCE ANALYSIS
For each anchor type in the output, verify:
- **well_controlled**: TIR 70-180% ≥ 85%, overnight 95-125 range maintained
- **overnight_hypo**: TIR 70-180% ≥ 60%, hits ≤70 mg/dL at least occasionally  
- **post_meal_spike**: TIR 70-180% ≥ 50%, shows clear meal spikes (but <300mg/dL)
- **brittle**: Shows variability but ceiling <5%, min >40mg/dL
- **All others**: No ceiling hits, TIR >30% (accepting wide variation for some)

#### 📈 COMPARISON TO BASELINE
If possible, compare to previous runs:
- Detection rate should be >0% (was 0% before calibration fixes)
- Truths detected should be >0 (was 0 before)
- No anchor should show degenerative flatlining or extreme volatility

## Acceptance Criteria
- [ ] **health_metric_edges > 0** (detectors firing on simulated data)
- [ ] **Detection rate > 0%** (measurable improvement from baseline)
- [ ] **Zero anchors with >5% ceiling hits** (maintaining safety)
- [ ] **All 180+ simulator unit tests pass** (no regressions)
- [ ] **Validation completes without errors** (script runs to finish)
- [ ] **At least 2 anchor types show truths_detected > 0** (pattern detection working)

## Connection to Other Work
This validates the calibration work done in:
- #213 (Fix cumulative drift across all anchors via pre-meal basal + drift rate)
- #214 (Calibrate post_meal_spike and brittle anchors)  
- #215 (Batch-calibrate remaining 8 anchors)

Success indicates the simulator is producing sufficiently realistic, patterned data for downstream applications like meal forecasting and pattern detection to work effectively. If detectors still show 0% detection, we need to investigate:
1. Truth-label generation window alignment
2. Detector threshold mismatch with new glucose ranges  
3. Missing event types in simulation output
4. Timing issues in truth vs detection window matching

## Troubleshooting Path if Fails
If detection rate remains 0%:
1. Check if simulator is producing visible meal spikes/runs
2. Verify truth-label generation is creating expected patterns
3. Test detectors manually on known-good data
4. Examine detector thresholds vs actual glucose ranges in output
5. Consider adjusting truth-label sensitivity or detector thresholds