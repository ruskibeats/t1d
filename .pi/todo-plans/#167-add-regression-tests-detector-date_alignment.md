# Clanker Ops #167: Add Regression Tests for Detector Date Alignment

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #167 is still open, assigned to you, and not blocked.
- Mark #167 in progress before implementation work.
- Read the full plan before editing files.

### While Working
- Keep changes scoped to this task and preserve unrelated user changes.
- Do not create skills, tools, scripts, or extra files unless the operator explicitly requested them or this plan names them.
- If you discover blockers, duplicates, missing context, or follow-up work, add/update Clanker Ops items instead of burying findings in prose.
- If the task cannot be completed, leave it in progress or mark it failed/deferred with a clear reason.

### Before Closing
- Run relevant verification checks.
- Update the Clanker Ops item with a completion summary.
- Include files changed, commands run, verification result, blockers/follow-ups, and estimated token burn.
- Mark the task completed only when the requested work is done and verified.

## Intended Outcome
Create regression tests that prevent recurrence of the detector date-range bug (wall-clock dates vs simulation dates causing zero overlap and zero detections).

## Root Context
The bug fixed in commit 07ae54e caused `health_metric_edges` to remain empty because:
- Detector queried `datetime.now() - 365 days` (Nov 2025 - May 2026)  
- Simulated data existed only in Jan 2025
- Zero date overlap = zero detections

## Step-by-Step

### 1. Identify test file location
- Check `tests/test_simulator_evaluator.py` for existing infrastructure
- Create `tests/test_detector_date_alignment.py` if needed

### 2. Write date alignment test
- Test that `_run_detectors` uses simulation dates, not wall-clock dates
- Mock a known simulation window (e.g., Jan 15-22, 2025)
- Assert detector queries only that window

### 3. Write edge creation test  
- Test that `health_metric_edges` are created for simulated data
- Use pytest fixtures for sim database setup
- Assert edge count > 0 after detector run

### 4. Write truth detection test
- Test that `sim_hidden_truths.is_detected` is set correctly
- Compare against min_glucose threshold (70 mg/dL)
- Assert true positives appear (not all false negatives)

## Verification
```bash
# Run the new tests
pytest tests/test_detector_date_alignment.py -v

# All tests should pass
# No regressions in existing simulator tests
```

## Closeout Report Template
```text
Summary: Created regression tests preventing detector date-range bug recurrence.
Files changed:
Commands run:
Verification:
Follow-ups created:
Blockers:
Token burn estimate:
Status:
```
