# Clanker Ops #14: [GRAPH] Event grouping foundation - add event_group_id to health_metrics

Status: completed
Owner: @tom_웃
Tags: #p0 #🧑 #backend #graph
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #14 is still open, assigned to you, and not blocked.
- Mark #14 in progress before implementation work.
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

[GRAPH] Event grouping foundation - assign event_group_id in ingestion
From GRAPH_TODO.md Section 0.1-0.3:
- event_group_id already exists in models (checked)
- Update ingestion flows to assign event_group_id to meals/exercise/insulin/sleep metrics
- Call link_event_group() from graph service to create same_event_as edges
- Update Fitbit/Garmin to use event_group_id from provider session IDs
