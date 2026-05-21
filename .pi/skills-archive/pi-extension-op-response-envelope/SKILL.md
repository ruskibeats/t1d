---
name: "pi-extension-op-response-envelope"
description: "Implement the Op/Response-Envelope pattern in a Pi extension: a closed tagged union (Op) that captures every reducer action outcome, a formatContent function with compiler-enforced exhaustive switch, and buildToolResult that wraps the formatted response with a replay-compatible details snapshot. Use when building CRUD tools in Pi extensions where reducer actions, formatted output, and branch-replay persistence must stay in sync."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

Use when a Pi extension has a CRUD tool (like `todo`) with a reducer and needs a disciplined pattern for:
- Capturing every reducer action outcome as a structured `Op` tagged union
- Formatting responses with compiler-enforced exhaustive matching
- Producing a replay-compatible `details` snapshot for Pi's branch replay mechanism
- Preventing "Op/Formatter drift" — the bug where adding a new reducer action but forgetting its Op variant and formatter branch silently produces `undefined` output

Common triggers:
- Adding a new action to an existing reducer and needing to wire it through to formatted output
- Building a new Pi extension tool from scratch that will persist state via branch replay
- Refactoring a monolithic tool where the reducer returns raw strings instead of structured Op types
- Encountering `undefined` in tool output after adding a new action type

Boundaries:
- Does NOT cover the state store pattern (atomic JSON persistence) — use `global:pi-extension-atomic-json-state` for that
- Does NOT cover the initial state/reducer decomposition — use `global:pi-extension-internal-refactoring` for that
- Assumes a pure reducer function already exists (or will be created as part of the extraction)
- Does NOT cover response formatting for overlay/TUI widgets (that's the view layer, not the tool response envelope)

## Prerequisites

- A Pi extension with at least one tool that uses a reducer pattern (state in, action+params in, new state out)
- The reducer returns some kind of result object (currently may return raw strings or unstructured objects)
- TypeScript project with `noImplicitReturns` or strict mode enabled (needed for exhaustive switch checking)
- A `TaskAction` or equivalent action type as a string union (e.g., `"create" | "update" | "list" | "get" | "delete" | "clear"`)

## Procedure

### Step 1: Define the `Op` Tagged Union

Create a closed tagged union type in your reducer module. Each variant represents one possible outcome of a reducer action. Include a dedicated `"error"` variant so callers can pattern-match without a side-channel boolean.

```typescript
// state/state-reducer.ts

export type Op =
  | { kind: "create"; taskId: number }
  | { kind: "update"; id: number; fromStatus: TaskStatus; toStatus: TaskStatus }
  | { kind: "delete"; id: number; subject: string }
  | { kind: "list"; statusFilter?: TaskStatus; includeDeleted: boolean }
  | { kind: "get"; task: Task }
  | { kind: "clear"; count: number }
  | { kind: "error"; message: string };
```

**Rules for Op variants:**
- Every action type must have exactly one matching Op variant (1:1 mapping)
- The `"error"` variant is **required** — even for actions that "can't fail" structurally
- Include enough context in each variant for the formatter to produce a meaningful string without re-reading state (e.g., `taskId`, `fromStatus`, `toStatus`, `subject`)
- Use primitive fields where possible — avoid embedding full objects unless needed for formatting (exceptions: `"get"` needs the full task for multi-line display)

### Step 2: Define the `ApplyResult` Return Type

```typescript
export interface ApplyResult {
  state: TaskState;  // The new state after the reducer ran
  op: Op;            // The structured outcome
}
```

### Step 3: Wire the Reducer to Return `{ state, op }`

Every case in the reducer must produce both a new state AND an Op. Use a helper for error branches:

```typescript
function errorResult(state: TaskState, message: string): ApplyResult {
  return { state, op: { kind: "error", message } };
}

export function applyTaskMutation(
  state: TaskState,
  action: TaskAction,
  params: TaskMutationParams,
): ApplyResult {
  switch (action) {
    case "create": {
      // ... create logic ...
      return {
        state: newState,
        op: { kind: "create", taskId: newTask.id },
      };
    }

    case "update": {
      // ... update logic ...
      return {
        state: newState,
        op: { kind: "update", id: task.id, fromStatus, toStatus },
      };
    }

    case "list": {
      return {
        state,  // List is read-only — state unchanged
        op: {
          kind: "list",
          includeDeleted: params.includeDeleted === true,
          ...(params.status ? { statusFilter: params.status } : {}),
        },
      };
    }

    case "get": {
      // ... find task ...
      return { state, op: { kind: "get", task: foundTask } };
    }

    case "delete": {
      // ... delete logic ...
      return {
        state: newState,
        op: { kind: "delete", id: task.id, subject: task.item },
      };
    }

    case "clear": {
      return {
        state: { tasks: [], nextId: 1 },
        op: { kind: "clear", count: previousCount },
      };
    }
  }
}
```

**Key invariant**: Read-only actions (`list`, `get`) return the original `state` unchanged. Mutating actions return a new state object. The response-envelope formatter does NOT mutate state — it reads from the returned state for display purposes.

### Step 4: Implement `formatContent` with Exhaustive Switch

Create a separate response envelope module (e.g., `tool/response-envelope.ts`) that owns the formatting. The `switch` statement must be closed — no `default` branch — so the TypeScript compiler enforces that every `Op.kind` variant has a corresponding format branch.

```typescript
export function formatContent(op: Op, state: TaskState): string {
  switch (op.kind) {
    case "create": {
      const t = state.tasks.find((x) => x.id === op.taskId);
      if (!t) return `Created #${op.taskId}`;
      return `Created #${t.id}: ${t.item} (pending)`;
    }

    case "update": {
      const transition =
        op.fromStatus !== op.toStatus
          ? ` (${op.fromStatus} → ${op.toStatus})`
          : "";
      return `Updated #${op.id}${transition}`;
    }

    case "delete":
      return `Deleted #${op.id}: ${op.subject}`;

    case "clear":
      return `Cleared ${op.count} tasks`;

    case "list": {
      let view = state.tasks;
      if (!op.includeDeleted)
        view = view.filter((t) => t.status !== "deleted");
      if (op.statusFilter)
        view = view.filter((t) => t.status === op.statusFilter);
      return view.length === 0
        ? "No tasks"
        : view.map(formatListLine).join("\n");
    }

    case "get":
      return formatGetLines(op.task, state);

    case "error":
      return `Error: ${op.message}`;
  }
}
```

**Critical rules:**
- **No `default` branch** — a `default` defeats the compiler's exhaustive check. If you add a `default`, future Op variants silently fall through to it and produce no output or wrong output.
- **Every Op kind must have a branch** — including `"error"`. If you omit it, the compiler catches the missing branch.
- **`get` and `list` may need access to `state`** — pass it as a second parameter for derived data (e.g., computing "blocks" relationships from the full task list).

### Step 5: Implement `buildToolResult` for Replay Snapshot

This function wraps `formatContent` and produces the full tool result envelope, including the `details` object that Pi's branch replay mechanism captures for state reconstruction.

```typescript
export interface TaskDetails {
  action: TaskAction;
  params: Record<string, unknown>;
  tasks: Task[];
  nextId: number;
  error?: string;
}

export function buildToolResult(
  action: TaskAction,
  params: TaskMutationParams,
  state: TaskState,
  op: Op,
): { content: Array<{ type: "text"; text: string }>; details: TaskDetails } {
  const text = formatContent(op, state);
  const details: TaskDetails = {
    action,
    params: params as Record<string, unknown>,
    tasks: state.tasks,
    nextId: state.nextId,
    ...(op.kind === "error" ? { error: op.message } : {}),
  };
  return { content: [{ type: "text", text }], details };
}
```

**Critical details:**
- The `details.tasks` field **must be the full task array** (not filtered/sorted) — the replay mechanism needs the complete state
- The `details.action` and `details.params` enable the replay mechanism to reconstruct what happened
- The `error` field is only included on error outcomes — this prevents replay from treating error states as valid data
- The `details` shape must remain **backward-compatible** across extension versions. Adding new optional fields is safe; removing or renaming existing fields will break replay for snapshots taken before the change.

### Step 6: Wire in the Tool Execute Handler

The tool's `execute` (or equivalent handler) should follow this flow:
1. Read current state (from store)
2. Dispatch action to reducer → get `{ state, op }`
3. If no error: commit new state (atomic write)
4. Build and return tool result envelope

```typescript
export async function execute(
  params: TodoParams,
): Promise<{ content: Array<{ type: "text"; text: string }>; details: TaskDetails }> {
  const state = getState();
  const result = applyTaskMutation(state, params.action, params as unknown as TaskMutationParams);
  
  if (result.op.kind !== "error") {
    commitState(result.state);
  }
  
  return buildToolResult(params.action, params as unknown as TaskMutationParams, result.state, result.op);
}
```

**The commit-before-format sequence matters**: `buildToolResult` reads from the new state (`result.state`) after it's been committed, so the details snapshot matches what's on disk.

## Pitfalls

1. **Adding a `default` branch to formatContent.** A `default: return "unknown"` defeats the compiler's exhaustive checking. New Op variants silently fall through and produce meaningless output. Always use an exhaustive `switch` with no `default` and `noImplicitReturns` enabled.

2. **Forgetting the `error` variant in formatContent.** Every reducer action can fail (invalid params, not-found, cycle detection). If you add an error Op variant but omit the corresponding `case "error"` branch, the compiler catches it — but only if you have no `default` branch. If you have a `default`, the error silently produces whatever the default returns.

3. **Embedding mutable objects in Op variants.** Op variants should use primitives (`taskId: number`, `subject: string`). Embedding full objects that the caller could mutate leads to confusing aliasing bugs. Exception: the `"get"` variant embeds a `Task` because multi-line formatting needs the full object, and the get result is not expected to survive beyond one formatting call.

4. **Inconsistent `details` shape breaks replay.** The `details` object is persisted by Pi's branch replay mechanism. If you rename `nextId` to `next_id`, all previously replayed snapshots silently drop the field. Keep the shape stable; add new fields as optional (`?:`).

5. **Omitting `error` from details on error paths.** If you include `error: null` or `error: undefined` in details for successful actions, replay may misbehave. Only include `error` on actual error results.

6. **Not passing `state` to formatContent for list/get.** The `"list"` and `"get"` Op variants need access to the full state to render derived relationships (e.g., "blocks" relationships). Always pass the new state as a second parameter to `formatContent`.

7. **Read-only actions mutating state.** The reducer should return the *original* state reference for read-only actions (`list`, `get`). Returning a new copy wastes memory and can confuse referential equality checks.

8. **Forgot the `error` Op variant entirely.** If your reducer can fail but has no `error` variant, you'll be tempted to use a hack like `{ kind: "list", error: true }`. This pollutes the Op type and defeats the pattern's purpose. Always include `{ kind: "error"; message: string }`.

## Verification

1. **Compiler exhaustive check**: After adding a new action type (e.g., `"archive"`) to `TaskAction`, the TypeScript compiler should produce errors in exactly two places:
   - The reducer's `switch (action)` — missing case
   - The `formatContent` switch — missing Op.kind branch
   This confirms the pattern catches drift at compile time.

2. **Every Op variant has a test**: Write at least one unit test per Op variant that calls `formatContent` with a synthetic Op and verifies the output string. Include a test for the `"error"` variant.

3. **Snapshot stability**: After any refactoring, run the tool's snapshot tests. The formatted output strings should be byte-identical to pre-refactor output (assuming the action/params are the same).

4. **Replay compatibility**: After changing the `details` shape, replay a previously captured snapshot. All required fields should still be present. Optional fields should gracefully default.

5. **No undefined output**: Run through all actions with valid params — the formatted output should never be `"undefined"` or `"null"`.

6. **Error path round-trip**: Call each action with intentionally invalid params (missing id, illegal transition). Verify the tool returns `{ kind: "error", message }` and that `formatContent` renders it as `"Error: ..."`.

## References

- Clanker Ops implementation: `tool/response-envelope.ts` — exhaustive formatContent + buildToolResult
- Clanker Ops reducer: `state/state-reducer.ts` — Op union + ApplyResult
- Clanker Ops types: `tool/types.ts` — TaskAction string union used for action matching
- TypeScript exhaustiveness checking: [TypeScript Handbook — Exhaustiveness checking](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#exhaustiveness-checking) using `never` return type
- Related skill: `global:pi-extension-atomic-json-state` — for the store/commit side of the data flow
- Related skill: `global:pi-extension-internal-refactoring` — for the initial state/reducer/view decomposition (the Op pattern is one deepening step within that workflow)