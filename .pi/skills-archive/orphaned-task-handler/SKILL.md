---
name: orphaned-task-handler
description: "Handle orphaned Clanker Ops tasks missing required plan files: identify tasks without corresponding plan files, evaluate work status, and mark appropriately (deferred/archive) with audit trail. Use when boarding hygiene reveals orphaned tasks."
version: 1
created: 2026-05-20
updated: 2026-05-20
---
## When to Use
Use this skill when boarding hygiene or plan audits reveal tasks without corresponding plan files, typically found during:
- Butler board audits
- Sprint review execution
- Duplicate detection passes
- End-of-day reporting

## Procedure
1. **Scan for missing plans**: Check `.pi/todo-plans/` for each active task
2. **Evaluate work status**:
   - Completed work → can archive without plan
   - In-progress work → requires plan creation first
   - Stale/no progress → candidate for deferral
3. **Apply rule**: "skip if missing plan files" → mark deferred
4. **Document audit trail** in EOD report or board notes
5. **Unassign self** after completion (per butler pattern)

## Pitfalls
- Don't defer work that's actively in progress
- Distinguish between planned+unplanned work vs truly orphaned
- Ensure deferral includes explanation for future agents
- Some tasks may have plans in different locations

## Verification
- Orphaned tasks marked deferred with audit note
- Active tasks have valid plan file references
- Board audit shows reduced orphaned task count
- Next butler audit finds fewer gaps