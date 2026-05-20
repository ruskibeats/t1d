# Clanker Ops #105: [GRAPH] Graph backfill script — rebuild historical graph edges from existing health_metrics

Status: completed
Owner: @worker
Tags: #p1 #backend #graph #script
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #105 is still open, assigned to you, and not blocked.
- Mark #105 in progress before implementation work.
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

### Closeout Report Template

```text
Summary:
Files changed:
Commands run:
Verification:
Follow-ups created:
Blockers:
Token burn estimate:
Status:
```

## Plan

**Missing from suggested implementation sequence in DATA_DESIGN_FLOW_PLAN.md**
- Create `scripts/backfill_graph_edges.py`
- For each user, scan historical metrics and create missing edges
- Run pattern detectors in backfill mode with edge persistence
- Report counts by edge type, handle upserts properly
- Verification: Script can rebuild entire graph from existing data
File: scripts/backfill_graph_edges.py
