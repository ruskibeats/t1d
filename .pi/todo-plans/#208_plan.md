# Clanker Ops #208: Simulator glucose calibration fix

## Intended Outcome
Pattern detectors produce non-zero detection rates on simulator data by fixing the glucose engine calibration so synthetic traces realistically vary within a detectable range (e.g., 80–250 mg/dL for well-controlled, with distinct post-meal rises ≥50 mg/dL).

## Root Cause
Two interacting bugs:

1. **Glucose engine caps at 400 mg/dL** — The well-controlled anchor has `basal_glucose_mean=(100, 130)` but the engine actually produces traces averaging ~396 mg/dL. The values hit the 400 ceiling constantly, leaving no room for detectable rises.

2. **Truth labels disagree with actual data** — The truth label generator expects peaks of 492+ but the glucose engine caps at 400, so actual data never matches truth expectations. The `detector_evidence` column is empty on all truths — the evaluator never finds a match.

## Evidence
- User 657 (run 29): 2016 glucose readings, nearly all at 400 mg/dL
- Pre-meal average: ~396 mg/dL → no room for a 50+ mg/dL spike
- All 16 completed runs show 0% detection rate across all pattern types
- `detector_evidence` is NULL on every single hidden truth

## Step-by-Step

### 1. Diagnose glucose engine baseline computation
- Check how `basal_glucose_mean` maps to actual generated values
- Look at `app/simulator/glucose_engine.py` — the circadian baseline + meal response + insulin + exercise model
- Determine why a mean of 100-130 produces actual output near 400

### 2. Fix the calibration
- Likely fix: adjust `meal_rise_factor` multiplier in anchors or add a glucose ceiling that allows dynamic range
- Or: fix the insulin/meal interaction that drives glucose too high
- Ensure "well_controlled" produces ranges like 80–200 mg/dL, not 350–400

### 3. Verify truth labels match fixed data
- After fix, truth label `expected_peak` should be reachable by the actual glucose trace
- Rerun evaluator — `is_detected` should become `true` for at least some truths

### 4. Run validation cohort
- Run `scripts/validate_cohort_168.py` after the fix
- Confirm non-zero detection rate, edges created, and detector_evidence populated

## Files to modify
- `app/simulator/glucose_engine.py` — core glucose generation
- `app/simulator/anchors.py` — anchor parameter ranges (maybe)
- `app/simulator/truth_labels.py` — if truth expectations need alignment

## Verification
- [ ] Well-controlled anchor produces glucose in 80–250 mg/dL range
- [ ] Post-meal spikes show ≥50 mg/dL rise from pre-meal baseline
- [ ] Truth labels match actual generated data
- [ ] `is_detected = true` for at least some truths after rerun
- [ ] `detector_evidence` populated after evaluator runs
- [ ] No regression in other anchor types

## Risks
- Overcorrecting could flatten all anchors to the same range (loss of diversity)
- Fixing one anchor but breaking others
- Truth label generator expects different dynamics than glucose engine can produce

## Audit (EOD Report-Back)
Append to .pi/EOD_AUDIT.md: (1) files changed, (2) verification results, (3) gaps/findings, (4) decisions, (5) estimated tokens.