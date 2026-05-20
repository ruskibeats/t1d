# Clanker Ops #23: [GRAPH] Graph service missing methods: get_edges_for_metric, get_recent_correlations, get_event_group, link_event_group

Status: completed
Owner: @worker
Tags: #p1 #backend #graph
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #23 is still open, assigned to you, and not blocked.
- Mark #23 in progress before implementation work.
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

MERGED with #31. Audit: link_event_group EXISTS, get_edges_for_metric EXISTS (get_neighbors), get_recent_correlations EXISTS (get_strongest_edges), get_event_group EXISTS (get_by_event_group in metrics service). Remaining: add get_event_group() to HealthGraphService + add GET /api/v1/metrics/graph/event-group/{event_group_id} endpoint. See .pi/todo-plans/#23_plan.md.
