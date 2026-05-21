# EOD Report - Daily Summary Generation

Status: pending
Tags: #housekeeping #remember #butler
Branch: dad_1805

## Intended Outcome
Daily EOD summary generated to `.pi/EOD_AUDIT.md` with completed work, open tasks, and blockers.

## Step-by-Step
1. Inspect `.pi/todo-state.json` for completed/pending tasks
2. Review sprint plans and open work
3. Generate structured summary:
   - Completed work
   - Open work (by assignee)
   - Blocked items
   - Sprint progress
4. Append to `.pi/EOD_AUDIT.md`

## Butler Workflow
After completion:
1. `todo update --assignee ""` to unassign self
2. Task returns to Don't Forget queue
3. Wait for next dispatch via `/run butler "eod report"`

## Verification
EOD report appended to `.pi/EOD_AUDIT.md` with all required sections.

## Audit (EOD Report-Back)
Append findings to `.pi/EOD_AUDIT.md`: (1) files inspected, (2) summary content, (3) gaps/findings, (4) decisions, (5) estimated tokens.