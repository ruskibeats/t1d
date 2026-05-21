---
name: "eod-report-generation"
description: "Generate daily end-of-day summary reports for Clanker Ops. Inspect todo-state.json, sprint plans, and open work, then output structured findings. Appends to .pi/EOD_AUDIT.md."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# EOD Report Generation — Daily Clanker Ops Summary

## Purpose
Generate structured daily summary reports for Clanker Ops board status. Aggregates completed tasks, open work, and findings from butler subtasks.

## When to Use
- Daily end-of-day reporting
- After completing butler subtasks (board hygiene, dupe comb, roster sync, etc.)
- Sprint review summaries
- Any need to summarize board state

## Procedure

### 1. Inspect todo-state.json
```bash
# Read current board state
cat .pi/todo-state.json
```
- Count completed tasks
- Identify pending tasks
- Check for blocked tasks

### 2. Review sprint plans
```bash
cat SPRINT_PLAN.md
```
- Note sprint status (complete/pending)
- Identify next sprint priorities
- Track sprint completion rate

### 3. Check open work
- Review .pi/todo-plans/ for active tasks
- Note task assignees and blockers
- Identify dependencies

### 4. Aggregate findings from butler subtasks
For each completed butler task (109-114):
- Board hygiene: stale blockedBy, ghost assignees, orphan plans
- Dupe comb: overlapping pending tasks (≥60% similarity)
- Roster sync: assignee mismatches
- Dependency triage: stuck tasks
- Plan audit: missing required sections
- Plan cleanup: orphaned plan files

### 5. Generate structured report
Append to .pi/EOD_AUDIT.md:
```markdown
## Completed Tasks
| # | Subject | Status | Verification |

## Files Modified Today
**Python**:
**Tests (ALL PASSING)**:
**Scripts**:
**Docs**:

## Test Results
[paste test output]

## Next Actions
1. [item]
```

### 6. Verification
- Report includes all completed tasks with verification
- Test results included
- Next actions identified
- Findings from butler tasks included

## Pitfalls
- Don't modify task content or assignees (butler directive)
- Report findings only, don't fix issues
- Include token burn estimates
- Keep report structured for easy scanning
- Verify all butler subtask findings are included

## Verification Checklist
- [ ] todo-state.json inspected
- [ ] Sprint plans reviewed
- [ ] All butler findings included
- [ ] Test results included
- [ ] Next actions identified
- [ ] Report appended to .pi/EOD_AUDIT.md