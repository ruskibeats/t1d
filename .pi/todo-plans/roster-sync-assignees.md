# Roster Sync - Verify Assignees Match CLANKER_ROSTER.md

Status: pending
Tags: #butler #daily #housekeeping
Branch: dad_1805

## Intended Outcome
Report of tasks with assignees not matching CLANKER_ROSTER.md entries.

## Step-by-Step
1. Read CLANKER_ROSTER.md for valid assignees
2. Scan todo-state.json for task assignees
3. Flag mismatches or unknown assignees
4. Report findings only

## Butler Workflow
After completion:
1. `todo update --assignee ""` to unassign self
2. Task returns to Don't Forget queue
3. Wait for next dispatch via `/run butler "roster sync"`

## Verification
Roster sync report in `.pi/EOD_AUDIT.md`

## Audit (EOD Report-Back)
Append findings to `.pi/EOD_AUDIT.md`: (1) files inspected, (2) mismatch count, (3) gaps/findings, (4) decisions, (5) estimated tokens.