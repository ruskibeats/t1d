# Clanker Ops #35: [DOCS.25.3] Update CONTEXT.md with formal graph node/edge/evidence definitions

Status: completed
Owner: @worker
Tags: #p1 #docs #graph
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #35 is still open, assigned to you, and not blocked.
- Mark #35 in progress before implementation work.
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

From scout #25. CONTEXT.md at /root/t1d/CONTEXT.md exists but lacks formal graph definitions. Update it to define: Health Metric node, Edge types (from GraphEdgeType), Evidence structure, Confidence scoring (0.0-1.0), Time Delay fields. Reference existing files: plan/specs/GRAPH_ARCHITECTURE.md for graph architecture, plan/specs/ARCHITECTURE_MAP.md for full architecture context, plan/decisions/CODEBASE_AUDIT.md for audit state.
