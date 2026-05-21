# Clanker Ops #168: Run 5-Patient, 7-Day Validation Cohort

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #168 is still open, assigned to you, and not blocked.
- Mark #168 in progress before implementation work.
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
Execute validation cohort (5 patients × 7 days) to verify the detector date-range fix works. Report before/after SQL evidence showing edges created and truths detected.

## Dependencies
- Commit 07ae54e applied (detector date-range fix)
- Database migration run if needed
- Valid DATABASE_URL config

## Step-by-Step

### 1. Prepare environment
- `cd /root/t1d`
- Activate virtual environment: `source venv/bin/activate`
- Verify DATABASE_URL is set

### 2. Run small cohort
```bash
python3 -m app.simulator.cli run \
  --patients 5 \
  --days 7 \
  --verbose
```

### 3. Verify edge creation
```sql
-- Should show hundreds of edges
SELECT COUNT(*) FROM health_metric_edges 
WHERE created_at > NOW() - INTERVAL '1 hour';
```

### 4. Verify truth detection
```sql
-- Should show non-zero detections
SELECT COUNT(*) FROM sim_hidden_truths 
WHERE is_detected = true;

-- Should show non-zero metrics
SELECT * FROM sim_detector_scores 
WHERE recall + precision > 0;
```

### 5. Report results
- Document before/after evidence
- Note any issues or anomalies
- Close out task

## Verification
- Edge count > 0 (pre-fix: 0 edges)
- Truth detection rate > 0% (pre-fix: 0%)
- Non-zero precision/recall/F1 in scores table

## Closeout Report Template
```text
Summary: Executed validation cohort proving detector fix works.
Files changed:
Commands run:
Verification: [SQL evidence here]
Follow-ups created:
Blockers:
Token burn estimate:
Status:
```
