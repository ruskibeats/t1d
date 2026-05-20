# Clanker Ops #25: [DOCS] Update CONTEXT.md, ARCHITECTURE_MAP.md, CODEBASE_AUDIT.md for graph architecture

Status: completed
Owner: @scout
Tags: #p1 #docs #graph
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #25 is still open, assigned to you, and not blocked.
- Mark #25 in progress before implementation work.
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

SCOUT FINDINGS (see scout-report-25.md): CONTEXT.md exists but lacks formal graph definitions (→ #35). ARCHITECTURE_MAP.md MISSING (→ #33). CODEBASE_AUDIT.md MISSING (→ #34). Graph service: app/metrics/graph_service.py with tests.
