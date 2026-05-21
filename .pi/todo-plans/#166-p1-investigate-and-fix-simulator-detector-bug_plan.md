# Investigate and Fix Simulator Detector Date-Range Bug

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm this task is still open, assigned to you, and not blocked.
- Mark this task in progress before implementation work.
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
Fix the root cause of 0 true positives in overnight_low detection by correcting the date range mismatch between simulated data and detector queries.

## Root Cause Summary
**Problem**: Detector queried `datetime.now() - timedelta(days=365)` (Nov 2025 - May 2026) while simulated data existed only in Jan 2025. Zero date overlap = zero detections.

## Step-by-Step

### 1. Inspect current code state
- Read `app/simulator/service.py` `_run_detectors` method
- Identify the date calculation logic

### 2. Apply the fix
- Modify `_run_detectors` signature to accept `sim_date_start` and `days_per_user`
- Replace wall-clock date calculation with actual simulation dates
- Update call site to pass correct parameters

### 3. Add regression tests
- Create test verifying detector date range matches simulation dates
- Add test asserting health_metric_edges are created for simulated data

### 4. Validate the fix
- Run small simulator cohort (2-5 patients, 7 days)
- Query SQL to verify edges populated and truths detected

## Verification
```sql
-- health_metric_edges should have records
SELECT COUNT(*) FROM health_metric_edges WHERE created_at > NOW() - INTERVAL '1 hour';

-- sim_hidden_truths should show detections
SELECT COUNT(*) FROM sim_hidden_truths WHERE is_detected = true;

-- sim_detector_scores should show non-zero metrics
SELECT * FROM sim_detector_scores WHERE precision + recall > 0;
```

## Commands to Run
```bash
# Run simulator
python3 -m app.simulator.cli run --patients 5 --days 7

# Check results
psql $DATABASE_URL -c "SELECT COUNT(*) FROM health_metric_edges;"
psql $DATABASE_URL -c "SELECT * FROM sim_detector_scores LIMIT 5;"
```

## Closeout Report Template
```text
Summary: [brief description of fix]
Files changed: 
Commands run: 
Verification: 
Follow-ups created: 
Blockers: 
Token burn estimate: 
Status: 
```
