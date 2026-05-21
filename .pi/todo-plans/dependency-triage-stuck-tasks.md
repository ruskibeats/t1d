# Dependency Triage - Walk blockedBy Chains, Find Stuck Tasks

Status: pending
Tags: #butler #daily #housekeeping
Branch: dad_1805

## Intended Outcome
Report of stuck tasks and broken dependency chains.

## Step-by-Step
1. Walk blockedBy chains for all blocked tasks
2. Find tasks whose blockers are already completed
3. Flag orphaned blockedBy references
4. Report findings only

## Butler Workflow
After completion:
1. `todo update --assignee ""` to unassign self
2. Task returns to Don't Forget queue
3. Wait for next dispatch via `/run butler "dependency triage"`

## Verification
Dependency report in `.pi/EOD_AUDIT.md`

## Audit (EOD Report-Back)
Append findings to `.pi/EOD_AUDIT.md`: (1) files inspected, (2) stuck tasks found, (3) gaps/findings, (4) decisions, (5) estimated tokens.