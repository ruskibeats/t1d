# Board Hygiene - Stale blockedBy, Ghost Assignees, Orphan Plans

Status: pending
Tags: #butler #daily #housekeeping
Branch: dad_1805

## Intended Outcome
Report of stale `blockedBy` chains, ghost assignees, and orphan plan files.

## Step-by-Step
1. Scan todo-state.json for tasks with stale `blockedBy`
2. Find ghost assignees (assigned to non-existent users)
3. Check `.pi/todo-plans/` for orphan files (no matching task)
4. Report findings only (do NOT fix)

## Butler Workflow
After completion:
1. `todo update --assignee ""` to unassign self
2. Task returns to Don't Forget queue
3. Wait for next dispatch via `/run butler "audit plans"`

## Verification
Findings reported in `.pi/EOD_AUDIT.md`

## Audit (EOD Report-Back)
Append findings to `.pi/EOD_AUDIT.md`: (1) files inspected, (2) findings count, (3) gaps/findings, (4) decisions, (5) estimated tokens.