# Clanker Ops #2: [GRAPH-B] Implement provenance tracking + confidence decomposition

Status: completed
Owner: @worker
Tags: #p1 #backend #graph
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #2 is still open, assigned to you, and not blocked.
- Mark #2 in progress before implementation work.
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

[CONSOLIDATED] Provenance tracking + confidence decomposition + detector version constants
From MASTER_TODO Sections 5A + 5B:
- Add provenance_json to health_metric_edges
- Add confidence_components_json to health_metric_edges
- Create shared scoring utility for graph detectors
- Add detector version constants
- Add provenance builder for consistent edge payloads
- Add confidence thresholds for UI/RAG wording (low/medium/high)
