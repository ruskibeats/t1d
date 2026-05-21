# Dupe Comb - Detect Overlapping Pending Tasks

Status: pending
Tags: #butler #daily #housekeeping
Branch: dad_1805

## Intended Outcome
Report of overlapping pending tasks with ≥60% intent overlap for human review.

## Step-by-Step
1. Scan all pending tasks in todo-state.json
2. Compare task subjects and descriptions for overlap
3. Report pairs with ≥60% similarity
4. Suggest consolidation candidates

## Butler Workflow
After completion:
1. `todo update --assignee ""` to unassign self
2. Task returns to Don't Forget queue
3. Wait for next dispatch via `/run butler "dupe comb"`

## Verification
Dupe report appended to `.pi/EOD_AUDIT.md`

## Audit (EOD Report-Back)
Append findings to `.pi/EOD_AUDIT.md`: (1) files inspected, (2) overlap pairs found, (3) gaps/findings, (4) decisions, (5) estimated tokens.