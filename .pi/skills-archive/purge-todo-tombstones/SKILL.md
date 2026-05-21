---
name: "purge-todo-tombstones"
description: "Detect and physically purge tombstoned (status=&quot;deleted&quot;) todo items from .pi/todo-state.json. Use when board views show stale deleted items, when the todo list count seems off, or during periodic state file cleanup. Covers inspecting for deleted entries, removing them with jq, and verifying the new count."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Purge Todo Tombstones

## When to Use

- Board/CLI output shows items marked with tombstone symbols (🗑, ⊘) that should be gone
- `todo list` (with `includeDeleted: true`) reveals items you thought were deleted
- Periodic cleanup of `.pi/todo-state.json`
- Count of items seems higher than expected due to accumulated deleted entries
- After bulk-deleting tasks that should no longer render

**Do NOT use when**: You want to keep a soft-delete audit trail of deleted tasks (this physically removes them).

## Procedure

### 1. Inspect the state file for tombstones

First, check how many tombstoned (status="deleted") items exist:

```bash
# Count items with status "deleted"
jq '[.items[] | select(.status == "deleted")] | length' .pi/todo-state.json

# List them with id and item name
jq '.items[] | select(.status == "deleted") | {id, item}' .pi/todo-state.json
```

### 2. Count items before purge

```bash
jq '.items | length' .pi/todo-state.json
```

### 3. Purge tombstoned items

Physically remove all items with `status == "deleted"` from the array:

```bash
jq '.items |= map(select(.status != "deleted"))' .pi/todo-state.json > .pi/todo-state.json.tmp && mv .pi/todo-state.json.tmp .pi/todo-state.json
```

This uses the write-to-temp + rename pattern (atomic) to prevent corruption.

### 4. Verify the purge

```bash
# Confirm no deleted-status items remain
jq '[.items[] | select(.status == "deleted")] | length' .pi/todo-state.json

# Confirm total is sane (should equal before-count minus deleted-count)
jq '.items | length' .pi/todo-state.json

# Validate JSON is still well-formed
jq '.' .pi/todo-state.json > /dev/null && echo "✅ Valid JSON"
```

### 5. Re-render the board

After purging, list tasks again to confirm the UI no longer shows tombstones:

```bash
jq '[.items[] | {id, item, status, owner}] | .[]' .pi/todo-state.json | head -40
```

## Pitfalls

- **Data loss**: This is irreversible. Once removed, tombstoned items cannot be recovered. Ensure you don't need any soft-delete audit trail before running the purge.
- **Race condition**: If another process (Clanker Ops extension, another pi session) writes to `.pi/todo-state.json` between the read and write, the temp file overwrite will lose that concurrent write. Avoid purging while other sessions are actively modifying the board.
- **Invalid JSON after bad jq**: Always validate the output before overwriting. The temp-file pattern (`> .tmp && mv`) at least prevents partial writes, but if jq itself fails, verify the temp file.
- **Closed todo IDs**: The task IDs of purged items are gone forever. If external references exist (plan files, cross-references), they'll point to nothing. Clean up associated artifacts first if needed.
- **git tracked state**: If `.pi/todo-state.json` is tracked in git, the purge will show as a diff of removed entries. This is noisy but harmless.

## Verification

- ✅ `jq '[.items[] | select(.status == "deleted")] | length'` returns `0`
- ✅ `jq '.'` exits without error (valid JSON)
- ✅ Board listing no longer shows tombstone entries
- ✅ Count matches expected: `before_count - deleted_count = after_count`