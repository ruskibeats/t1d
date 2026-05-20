# Clanker Ops #37: [AUDIT] Prune agent roster to T1D-relevant subset and remove irrelevancies

Status: completed
Tags: #audit, housekeeping
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #37 is still open, assigned to you, and not blocked.
- Mark #37 in progress before implementation work.
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

Audit all 62 agents in Clanker Roster. Remove iOS-specific (healthkit), irrelevant (writing-fragments, obsidian-vault), overlapping skills. Keep core: worker, reviewer, planner, researcher, scout, diagnose, tdd, prototype, review, improve-codebase-architecture, impeccable, design-taste-frontend. Create curated list of ~20 high-value agents for T1D Companion Clanker Ops.
