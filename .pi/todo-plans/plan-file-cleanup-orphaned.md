# Plan File Cleanup - Remove Orphaned .md Files

Status: pending
Tags: #butler #housekeeping #weekly
Branch: dad_1805

## Intended Outcome
Report of orphaned plan files (no matching task in todo-state.json).

## Step-by-Step
1. List all `#*_plan.md` files in `.pi/todo-plans/`
2. Check if each task ID exists in todo-state.json
3. Report orphan file paths
4. Do NOT delete (report only)

## Butler Workflow
After completion:
1. `todo update --assignee ""` to unassign self
2. Task returns to Don't Forget queue
3. Wait for next dispatch via `/run butler "plan cleanup"`

## Verification
Orphan plan report in `.pi/EOD_AUDIT.md`

## Audit (EOD Report-Back)
Append findings to `.pi/EOD_AUDIT.md`: (1) files inspected, (2) orphan count, (3) gaps/findings, (4) decisions, (5) estimated tokens.