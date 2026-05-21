---
name: "atomic-json-state-persistence"
description: "Implement crash-safe, atomic JSON state persistence for Node.js/TypeScript CLI tools and extensions. Uses write-to-temp + rename pattern to prevent corrupted state files during crashes or concurrent access."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

Use when a Node.js/TypeScript tool or Pi extension needs to persist structured state (JSON) to disk and must guarantee file integrity even if the process crashes, is killed, or encounters concurrent writes.

Common scenarios:
- Task board state (todo apps, kanban boards)
- Configuration that changes at runtime
- Session or queue state for CLI tools
- Pi extension state stores
- Any tool where a corrupted state file would be catastrophic

## Procedure

### 1. Define State Types

```typescript
// state.ts
export interface TaskState {
  tasks: Task[];
  nextId: number;
}

export const EMPTY_STATE: TaskState = {
  tasks: [],
  nextId: 1,
};
```

### 2. Implement Atomic Commit

```typescript
// store.ts
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import type { TaskState } from "./state.js";

const STATE_PATH = ".pi/todo-state.json";

function readState(): TaskState | null {
  if (!existsSync(STATE_PATH)) return null;
  try {
    const raw = readFileSync(STATE_PATH, "utf-8");
    return JSON.parse(raw) as TaskState;
  } catch {
    return null; // Corrupted file — caller must handle
  }
}

/**
 * Atomic commit: write to temp file, then rename.
 * On crash, the old file remains intact.
 */
export function commitState(state: TaskState): void {
  const dir = dirname(STATE_PATH);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

  const tempPath = `${STATE_PATH}.tmp`;
  writeFileSync(tempPath, JSON.stringify(state, null, "\t") + "\n", "utf-8");
  renameSync(tempPath, STATE_PATH);
}
```

### 3. Wire Reducer Output to Commit

```typescript
// state-reducer.ts or tool execute()
export interface ApplyResult {
  state: TaskState;
  task?: Task;
  error?: string;
}

export function applyTaskMutation(
  state: TaskState,
  action: TaskAction,
  params: TaskMutationParams
): ApplyResult {
  // ... reducer logic returns new state
  return { state: nextState, task: updatedTask };
}
```

```typescript
// In the tool/command handler:
const result = applyTaskMutation(currentState, action, params);
if (!result.error) {
  commitState(result.state);  // Atomic write
}
```

### 4. Initialize with Fallback

```typescript
export function loadOrInitState(): TaskState {
  const existing = readState();
  if (existing) return existing;

  commitState(EMPTY_STATE);
  return EMPTY_STATE;
}
```

## Pitfalls

- **Do NOT** use `writeFileSync(path, json)` directly on the canonical file. A crash mid-write leaves truncated/corrupted JSON.
- **Do NOT** use async fs promises for the commit unless you absolutely need concurrency. Sync operations in CLI tools/extensions are simpler and sufficient for single-process workloads.
- **Always** create parent directories with `mkdirSync(..., { recursive: true })` before writing.
- **Handle parse errors gracefully** — a corrupted state file should fall back to empty/initial state, not crash the process.
- **Temp file naming** — use a deterministic suffix (`.tmp`) so stale temp files can be cleaned up if `renameSync` itself fails (extremely rare).

## Verification

1. Write state successfully → read it back, assert deep equality.
2. Simulate crash: write temp file, kill process before rename → verify original file untouched.
3. Test concurrent writes (if applicable): rapid sequential commits should never produce invalid JSON.

## Variations

- **With backups**: Keep 1-2 rotated backups (`state.json.1`, `state.json.2`) by copying before rename for extra safety.
- **With locking**: For multi-process access, add `proper-lockfile` or flock around the commit.
- **Pretty vs minified**: Use `JSON.stringify(state, null, "\t")` for human-readable state files; omit for high-frequency writes.

## References

- Node.js `fs.renameSync` is atomic on POSIX and near-atomic on Windows (within the same volume).
- Pattern derived from SQLite WAL commit semantics and common database journaling strategies.