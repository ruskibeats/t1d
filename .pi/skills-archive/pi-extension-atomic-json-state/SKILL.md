---
name: "pi-extension-atomic-json-state"
description: "Replace a Pi extension's in-memory module state with durable JSON file persistence using atomic writes and timestamp-based merge reconciliation. Use when a Pi extension's state drifts between branch-replay state and external CLI/tool mutations, or when state must survive session restarts."
version: 3
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

Use when a Pi extension currently stores state in a module-level variable (`let state = ...`) and needs one or more of the following:
- State must survive Pi session restarts (branch replay is insufficient or unreliable)
- An external CLI or tool mutates the same state outside the Pi tool system
- Multiple processes need a consistent view of the same state
- Board renderers or external scripts read state directly from disk

Common symptoms that trigger this skill:
- Tasks created via a bash CLI are invisible to the Pi `todo` tool
- The board renderer shows different data than the Pi overlay
- State changes made while Pi is offline are lost on next session start
- Corruption or partial writes after crashes

Boundaries:
- Does NOT cover database-backed state (SQLite/PostgreSQL) — use an ORM or query builder instead
- Does NOT cover simple ephemeral state that truly only lives for one Pi session
- Assumes JSON is the appropriate serialization format (not binary, not YAML)

## Prerequisites

- Extension has a clear state schema (e.g., `TaskState`, `ConfigState`)
- Extension has a known JSON file path (convention: `.pi/<name>-state.json`)
- State objects have an `updatedAt: string` (ISO 8601) field for conflict resolution
- Node.js `fs` and `path` APIs available

## Procedure

### Step 1: Remove the Module-Level State Cell

Before:
```typescript
let state: TaskState = { tasks: [...EMPTY_STATE.tasks], nextId: EMPTY_STATE.nextId };
```

After: delete the module-level variable entirely. The JSON file becomes the single source of truth.

### Step 2: Implement JSON File Reader with Schema Validation

```typescript
import { existsSync, readFileSync } from "node:fs";

const STATE_PATH = ".pi/todo-state.json"; // adjust for your extension

function readJsonState(): { items: Task[] } | null {
  if (!existsSync(STATE_PATH)) return null;
  try {
    const raw = readFileSync(STATE_PATH, "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    // Schema guard — validate the shape you expect
    if (
      parsed &&
      typeof parsed === "object" &&
      "items" in parsed &&
      Array.isArray((parsed as { items: unknown }).items)
    ) {
      return parsed as { items: Task[] };
    }
    return null;
  } catch {
    return null;
  }
}
```

Add validation guards appropriate to your schema. Never trust raw JSON on disk.

### Step 3: Implement Atomic Write

```typescript
import { dirname, writeFileSync, renameSync, mkdirSync } from "node:path";

function atomicWrite(filePath: string, data: string): void {
  const dir = dirname(filePath);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  const tempPath = filePath + ".tmp";
  writeFileSync(tempPath, data, "utf-8");
  renameSync(tempPath, filePath);
}
```

Atomicity guarantee: `renameSync` is atomic on POSIX and nearly atomic on Windows. Crash during `writeFileSync` leaves `.tmp` file behind; original file is untouched.

### Step 4: Implement Timestamp-Based Merge Logic

When Pi branch replay reconstructs state, it may conflict with mutations made by the external CLI while Pi was offline. Resolve using `updatedAt` timestamps (last-write-wins):

```typescript
function mergeStates(replayed: TaskState, currentItems: Task[]): Task[] {
  const currentMap = new Map(currentItems.map((t) => [t.id, t]));
  const replayedMap = new Map(replayed.tasks.map((t) => [t.id, t]));
  const allIds = new Set([...currentMap.keys(), ...replayedMap.keys()]);
  const merged: Task[] = [];

  for (const id of allIds) {
    const current = currentMap.get(id);
    const replayedTask = replayedMap.get(id);
    if (!current) {
      merged.push(replayedTask!);
    } else if (!replayedTask) {
      merged.push(current);
    } else {
      const currentTime = new Date(current.updatedAt).getTime();
      const replayedTime = new Date(replayedTask.updatedAt).getTime();
      merged.push(replayedTime > currentTime ? replayedTask : current);
    }
  }
  merged.sort((a, b) => a.id - b.id);
  return merged;
}
```

**Critical**: Every mutation to `updatedAt` must use `new Date().toISOString()` in the reducer or mutation layer.

### Step 5: Update Public Accessors

```typescript
export function getState(): TaskState {
  const json = readJsonState();
  if (json) return toTaskState(json.items);
  return { tasks: [...EMPTY_STATE.tasks], nextId: EMPTY_STATE.nextId };
}

export function getTodos(): readonly Task[] {
  return getState().tasks;
}

export function getNextId(): number {
  return getState().nextId;
}
```

Always read from disk. No caching layer at the module level.

### Step 6: Update Commit and Replay Seams

```typescript
export function commitState(next: TaskState): void {
  atomicWrite(STATE_PATH, JSON.stringify(toJsonPayload(next), null, 2) + "\n");
}

export function replaceState(next: TaskState): void {
  const json = readJsonState();
  if (json && json.items.length > 0) {
    // JSON has valid data — merge with replayed state
    const merged = mergeStates(next, json.items);
    commitState({ tasks: merged, nextId: deriveNextId(merged) });
  } else if (json && json.items.length === 0) {
    // JSON exists but is empty — write replayed state only if it has items
    if (next.tasks.length > 0) {
      commitState(next);
    }
    // Otherwise keep the empty JSON file as-is
  } else {
    // JSON doesn't exist or couldn't be read — write replayed state
    // only if it has actual content (prevents wiping valid data during replay failures)
    if (next.tasks.length > 0) {
      commitState(next);
    }
  }
}
```

- **`commitState`** is the post-reducer write seam (called after every mutation)
- **`replaceState`** is the branch-replay seam (called on session lifecycle events)
- **Empty-state guard**: `replaceState` only writes replayed state if `next.tasks.length > 0`. This prevents a replay that found no tool results from overwriting a valid JSON file on disk. Without this guard, a failed replay (e.g., branch read error) silently wipes all existing data.

The three-branch logic:
1. **JSON has data**: always merge with replay and write
2. **JSON is empty**: write replay only if replay has content (otherwise keep empty)
3. **No JSON file**: write replay only if replay has content (otherwise skip — prevents wiping valid data on first cold replay)

### Step 7: Update Reset/Test Helpers

```typescript
export function __resetState(): void {
  commitState({ tasks: [...EMPTY_STATE.tasks], nextId: EMPTY_STATE.nextId });
}
```

Tests and setup hooks must write to the JSON file, not a module variable.

### Step 8: Update Reducer to Maintain Timestamps

Ensure every mutation path sets `updatedAt`:

```typescript
const updated: Task = { ...current, status: newStatus, updatedAt: new Date().toISOString() };
```

On create, set both `createdAt` and `updatedAt`:

```typescript
const newTask: Task = {
  id: state.nextId,
  status: "pending",
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};
```
## Pitfalls
1. **Race conditions between Pi and external CLI.** The timestamp merge reduces but does not eliminate races. If both write within the same millisecond, merge behavior is arbitrary. For high-contention scenarios, add a file lock or move to a database.
2. **Missing `updatedAt` breaks merge.** If the external CLI mutates without setting `updatedAt`, the merge may choose stale data. Enforce timestamp updates in ALL mutation paths, including bash scripts.
3. **JSON parse failures return null.** A corrupted state file silently falls back to empty state. Consider logging parse failures or backing up the corrupt file for inspection.
4. **Atomic write temp files accumulate on crash.** If the process dies between `writeFileSync(temp)` and `renameSync`, a `.tmp` file is left behind. A cleanup job can remove `*.tmp` files older than a threshold.
5. **Performance on very large state files.** Reading the entire JSON file on every `getState()` call is fine for hundreds of items but scales poorly to thousands. If state grows large, add an in-memory LRU cache with explicit invalidation tied to `commitState`.
6. **Branch replay still produces its own state snapshot.** Pi's branch replay mechanism does not know about the JSON file. `replaceState` must be called in lifecycle handlers (`session_start`, `session_compact`) to merge replayed state with file state.
7. **Do NOT use `require("fs/promises")` in hot paths.** Synchronous `fs` operations block the event loop but ensure atomicity in a single-threaded extension context. If async is required, wrap carefully and serialize accesses.
8. **Empty-state guard is critical.** Without the `next.tasks.length > 0` guard in `replaceState`, a Pi session restart where branch replay finds no tool results (e.g., first cold start, replay read failure) will overwrite the existing JSON file with an empty state array, permanently losing all data. Always check `next.tasks.length > 0` before writing on the "no JSON file" or "empty JSON file" branches.
## Verification

1. `getState()` returns the latest data after a bash CLI mutation — no Pi restart required
2. `commitState(...)` produces a valid `.pi/todo-state.json` (or your path) immediately
3. Kill Pi, run external CLI mutations, restart Pi — replayed state merges correctly with no data loss
4. Simultaneous `updatedAt` timestamps in Pi and CLI result in deterministic last-write-wins behavior
5. `__resetState()` clears the JSON file to the empty state; no module variable retains old data
6. Corrupt JSON file (e.g., trailing comma) does not crash the extension; it falls back to empty state
7. Board renderer, external scripts, and Pi tool all read the same canonical state after any mutation

## References

- Clanker Ops state reducer: `state/state-reducer.ts` — timestamp maintenance
- Clanker Ops store: `state/store.ts` — atomic write and merge implementation
- Pi extension lifecycle: `index.ts` — `session_start` / `session_compact` replay hooks
- Timestamp hardening: `pi-extension-schema-timestamp-hardening` skill