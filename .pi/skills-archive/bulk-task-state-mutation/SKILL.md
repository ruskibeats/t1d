---
name: "bulk-task-state-mutation"
description: "Implement bulk task state mutations in a Clanker Ops state reducer: parse comma-separated task IDs from CLI input, extract named flags (--status, --assigned, --tag), iterate over IDs applying the same update mutation, and return a bulk outcome with updated count. Use when adding a /clanker bulk command or any batch state transition in the Clanker Ops system."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

- You're adding a `/clanker bulk #10,#11,#12 --status in_progress` command to the Clanker Ops CLI router
- You need to apply the same state mutation (status change, assignment, tag update) to multiple tasks at once
- Your state reducer uses the `applyTaskMutation` / `TaskMutationParams` pattern from Clanker Ops

Do **not** use for:
- Single-task updates (use the existing `update` action in the reducer)
- Operations that affect all tasks (write a dedicated handler instead)
- Non-Clanker Ops state management (this skill depends on Clanker Ops Task/TaskAction types and reducer conventions)

## Procedure

### 1. Register the bulk action in types

In `tool/types.ts`, add `"bulk"` to the `TaskAction` union:

```typescript
export type TaskAction = "create" | "update" | "list" | "get" | "delete" | "clear" | "dispatch" | "bulk";
```

### 2. Add bulk outcome to the Op union

In the state reducer's Op union, add:

```typescript
export type Op =
  | { kind: "create"; taskId: number }
  | { kind: "update"; id: number; fromStatus: TaskStatus; toStatus: TaskStatus }
  | { kind: "bulk"; count: number; action: string }
  // ... other kinds
  | { kind: "error"; message: string };
```

### 3. Implement bulk mutation in the reducer

In `applyTaskMutation`, add a `"bulk"` case:

```typescript
case "bulk": {
  const ids = params.ids as number[] | undefined;
  const bulkAction = params.action as string | undefined;
  if (!ids?.length) return errorResult(state, "ids required for bulk");
  if (!bulkAction && !params.status && !params.assigned && !params.tags) {
    return errorResult(state, "at least one mutation field required for bulk");
  }

  let currentState = state;
  let updatedCount = 0;

  for (const id of ids) {
    const idx = currentState.tasks.findIndex((t) => t.id === id);
    if (idx === -1) continue;  // silent skip — non-existent IDs don't error

    const subResult = applyTaskMutation(currentState, "update", { ...params, id });
    if (subResult.op.kind !== "error") {
      currentState = subResult.state;
      updatedCount++;
    }
  }

  return {
    state: currentState,
    op: { kind: "bulk", count: updatedCount, action: params.status as string || "update" },
  };
}
```

**Key design decisions:**
- Reuses the existing `"update"` mutation for each task — no duplicate logic
- Silently skips non-existent IDs (fails fast only on structural errors like missing `ids` array)
- Spreads `params` so that shared fields (status, assigned, tags) flow through to each sub-call, but overwrites `id` per iteration
- Returns the count of successfully updated tasks so the caller can confirm partial success

### 4. Register the bulk command in the router

In `commands/router.ts`, add the handler to the handlers record:

```typescript
const handler: Record<string, Handler> = {
  bulk: handleBulk,
  // ... other handlers
};
```

### 5. Implement the bulk CLI handler

```typescript
async function handleBulk(ctx: CommandContext): Promise<boolean> {
  const parts = ctx.input.split(" ");

  // Parse comma-separated IDs: #10,#11,#12
  const idMatch = ctx.input.match(/#(\d+)(?:,#(\d+))*/);
  if (!idMatch) {
    ctx.notify("Usage: /clanker bulk #10,#11,#12 --status in_progress", "error");
    return false;
  }

  const ids = ctx.input.match(/#\d+/g)!.map((s: string) => parseInt(s.replace("#", "")));

  // Extract named flags
  const params: Record<string, unknown> = { ids };

  const statusIdx = ctx.input.indexOf("--status ");
  if (statusIdx >= 0) {
    const val = ctx.input.slice(statusIdx + 9).split(" ")[0];
    params.status = val;
  }
  const assignIdx = ctx.input.indexOf("--assigned ");
  if (assignIdx >= 0) {
    const val = ctx.input.slice(assignIdx + 11).split(" ")[0];
    params.assigned = val;
  }

  const result = applyTaskMutation(getState(), "bulk", params as TaskMutationParams);
  if (result.op.kind === "error") {
    ctx.notify(`Bulk failed: ${result.op.message}`, "error");
    return false;
  }

  commitState(result.state);
  ctx.notify(`✅ Bulk updated ${result.op.count} tasks`, "info");
  return true;
}
```

### 6. Wire help text

Update the clanker help text to include the bulk subcommand:

```
  /clanker bulk #10,#11,#12 --status in_progress   Bulk update tasks
```

## Pitfalls

- **Partial success**: Some IDs may be invalid/deleted and silently skipped. Always show the count of actually updated tasks so users know if something was missed.
- **Recycle mutations**: Do NOT write a separate bulk mutation body — reuse `"update"` per task to keep validation logic (transition legality, self-block, cycles) consistent.
- **Flag parsing order**: Extract flags from the raw `ctx.input` string, not from `parts` array — the positional ID list makes parts-based parsing fragile with variable-length ID lists.
- **Type casting**: Cast `params.ids` and `params.action` explicitly with `as` since `TaskMutationParams` may not declare these fields natively. Keep the `as` close to the access site.
- **No rollback**: The bulk mutation is NOT transactional — if task #10 succeeds and task #12 fails, #10's change is already committed to currentState. This is acceptable for task boards; document in comments.
- **Large batches**: Very large ID lists (>100) may loop slowly. Consider a batch size limit or progress reporting for extreme cases.

## Verification

1. `/clanker bulk #10,#11 --status in_progress` updates both tasks and returns count=2
2. `/clanker bulk #999` (non-existent ID) returns count=0 with no error
3. `/clanker bulk` (no IDs) returns an error: "ids required for bulk"
4. `/clanker bulk #10 --status nonexistent` returns error from the underlying update mutation
5. `/clanker bulk #10` (no flags) returns error: "at least one mutation field required for bulk"
6. After bulk update, re-rendering the board shows updated statuses/symbols
7. The bulk command is listed in `/clanker help` output