---
name: "clanker-task-update"
description: "Procedure for safely updating Clanker Ops task states (status, assignee) in .pi/todo-state.json."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
Use when updating task status or assignment in `Clanker Ops` that requires direct editing of `.pi/todo-state.json`.

## Procedure
1. **Locate the Task**: Use `read` on `.pi/todo-state.json` to find the exact block for the task.
2. **Context Selection**: Select enough lines of the task block to make `oldText` unique (usually the `id`, `item`, and surrounding fields).
3. **Draft Edit**: Create an `edit` call targeting the specific field (`assigned` or `status`) to be changed.
4. **Safety Check**: Ensure `oldText` matches exactly (newlines, whitespace, indentation).

## Pitfalls
- **Brittle Matching**: Changing too little context can lead to non-unique matches; changing too much can lead to brittle matches if spacing/formatting changes slightly.
- **Malformed JSON**: Always ensure the resulting JSON is valid.

## Verification
1. Run `read` after the edit to confirm the update.
2. Check `clanker` tool status to verify the change is registered.