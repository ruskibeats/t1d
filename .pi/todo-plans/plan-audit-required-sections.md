# Plan Audit - Verify All Plan Files Have Required Sections

Status: pending
Tags: #butler #housekeeping #weekly
Branch: dad_1805

## Intended Outcome
Report of plan files missing required sections (Intended Outcome, Step-by-Step, Verification, Audit).

## Step-by-Step
1. Scan `.pi/todo-plans/#*_plan.md` files
2. Check for required sections
3. Flag missing sections
4. Report findings only

## Butler Workflow
After completion:
1. `todo update --assignee ""` to unassign self
2. Task returns to Don't Forget queue
3. Wait for next dispatch via `/run butler "plan audit"`

## Verification
Plan audit report in `.pi/EOD_AUDIT.md`

## Audit (EOD Report-Back)
Append findings to `.pi/EOD_AUDIT.md`: (1) files inspected, (2) missing sections count, (3) gaps/findings, (4) decisions, (5) estimated tokens.