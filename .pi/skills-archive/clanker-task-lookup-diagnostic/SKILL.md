---
name: "clanker-task-lookup-diagnostic"
description: "Diagnose why a Clanker Ops task ID (e.g., #11) is not found in the current board state."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
Use this procedure when a Clanker Ops task ID (e.g., `#11`) is reported as "not found" or you suspect a task might be missing from the board.

## Procedure
1. **Locate Task State**: Access the current project's Clanker Ops state file, typically located at `.pi/todo-state.json`.
2. **List Tasks**: Read the contents of `.pi/todo-state.json` and extract the `items` array.
3. **Verify ID**: Search the `items` array for the specific task ID (`id` field).
4. **Check Backups**: If the ID is not in the active file, check for recent backup files (e.g., `.pi/todo-state.json.backup-*`) to see if the task was recently archived or accidentally removed.
5. **Reconcile**: If the task appears in a backup but not in the active file, create a new task or restored item as needed, or report the discrepancy for audit.

## Pitfalls
- **State Stale**: `todo-state.json` might be locked or un-synced. Ensure you are reading the latest file.
- **Missing Backups**: If no recent backups are found, data loss might have occurred - escalate to manual recovery or audit logs.

## Verification
- Confirm the task ID exists in the `items` array of the active `todo-state.json`.
- If restored from a backup, verify the status matches the intended state.