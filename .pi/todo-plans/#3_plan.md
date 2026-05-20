# Clanker Ops #3: [GRAPH-C] Add event-group API endpoint + auth for graph endpoints

Status: completed
Owner: @scout
Tags: #p1 #api #backend #graph
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #3 is still open, assigned to you, and not blocked.
- Mark #3 in progress before implementation work.
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

SCOUT FINDINGS (see scout-report-3.md): event_group_id EXISTS in models/ingestion. get_event_group() method EXISTS. MISSING: event-group endpoint (→ #31). MISSING: auth migration on 13 routes (→ #32).
