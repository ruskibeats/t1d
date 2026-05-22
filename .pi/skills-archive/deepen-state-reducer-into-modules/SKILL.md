---
name: "deepen-state-reducer-into-modules"
description: "Deepen a large state reducer (or any monolith function) by extracting focused modules for validation, construction, and mutation. Use when a reducer/tool file exceeds 200 lines and mixes validation, creation, and update logic."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Deepen a State Reducer Into Focused Modules

## When to Use

Extract focused modules from a large state reducer (or any monolith file that manages state transitions). Use when:

- A reducer or tool file exceeds ~200 lines
- The file mixes 3+ distinct responsibilities (validation, construction, mutation, persistence)
- Status transition logic is scattered or duplicated
- You need to add new actions without bloating the reducer further
- Unit tests are hard to write because test setup requires the entire state

Do NOT use for:
- Reducers under 100 lines with simple logic
- Reducers that handle only 1-2 simple state transitions
- First-time experimentation — let the shape settle before deepening

## Procedure

### Step 1 — Analyze the reducer's responsibilities

Read the entire reducer/function. Identify every responsibility domain:

| Domain | Example | Extract as |
|--------|---------|------------|
| **Validation** | Status transition rules, field requirements, cycle detection | `transition-validator.ts` |
| **Construction** | Creating new task/item instances with defaults | `task-factory.ts` |
| **Mutation** | Applying field updates, metadata changes, dependency changes | `update-mutator.ts` |
| **Persistence** | Writing to disk, syncing state | `store.ts` or `persistence.ts` |
| **Selection/Query** | Filtering, sorting, counting tasks | `selectors.ts` |

### Step 2 — Extract Transition Validator

Create `transition-validator.ts`:

```typescript
/**
 * TransitionValidator — Encapsulates valid status transitions.
 * All valid transition rules live in ONE place.
 */

import type { TaskStatus } from "../tool/types.js";

export const VALID_TRANSITIONS: Record<TaskStatus, ReadonlySet<TaskStatus>> = {
  pending: new Set(["in_progress", "completed", "deleted", "failed", "cancelled", "deferred"]),
  in_progress: new Set(["pending", "completed", "deleted", "failed", "cancelled", "deferred"]),
  completed: new Set(["deleted", "failed", "cancelled"]),
  // ... etc
};

export function isTransitionValid(from: TaskStatus, to: TaskStatus): boolean {
  if (from === to) return true;
  return VALID_TRANSITIONS[from]?.has(to) ?? false;
}
```

Include:
- `VALID_TRANSITIONS` map (source → allowed destinations as `ReadonlySet`)
- `isTransitionValid(from, to)` — returns boolean
- `getValidDestinations(from)` — returns the allowed set
- `isReversible(from, to)` — checks if you can go back

**Pitfall**: Use `ReadonlySet<TaskStatus>` not `Set<TaskStatus>` for the map values. This prevents accidental mutation of the transition table at runtime and signals intent to future readers.

### Step 3 — Extract Task/Item Factory

Create `task-factory.ts`:

```typescript
/**
 * TaskFactory — Creates new Task instances with defaults.
 * Centralizes construction so all callers produce the same shape.
 */

export const EMPTY_STATE_TASK: Task = {
  id: 0, item: "", status: "pending",
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export function createTask(item: string, extra?: Partial<Task>): Task {
  return {
    ...EMPTY_STATE_TASK,
    item,
    id: crypto.randomUUID ? crypto.randomUUID() : Date.now(),
    ...extra,
    updatedAt: new Date().toISOString(),
  };
}

export function cloneTask(task: Task, overrides?: Partial<Task>): Task {
  return { ...task, ...overrides, updatedAt: new Date().toISOString() };
}
```

Include:
- `createTask(item, extra?)` — minimal constructor with defaults
- `createTaskWithFields(fields)` — full constructor with validation
- `cloneTask(task, overrides?)` — immutable update with timestamp bump

### Step 4 — Extract Update Mutator

Create `update-mutator.ts`:

```typescript
/**
 * UpdateMutator — Handles field-wise mutations with validation.
 * Encapsulates the repetitive field-by-field update logic.
 */

export function validateUpdateParams(task: Task, params: UpdateParams, state: TaskState):
  { valid: true } | { valid: false; error: string } {

  if (!params.status && !hasMutableField(params)) {
    return { valid: false, error: "at least one mutable field required" };
  }
  if (params.status && !isTransitionValid(task.status, params.status)) {
    return { valid: false, error: `illegal transition ${task.status} → ${params.status}` };
  }
  // Check cycle detection for dependency changes
  if (params.addBlockedBy?.length) {
    if (detectCycle(state.tasks, task.id, [...(task.blockedBy ?? []), ...params.addBlockedBy])) {
      return { valid: false, error: "would create a cycle in blockedBy graph" };
    }
  }
  return { valid: true };
}
```

Include:
- `validateUpdateParams(task, params, state)` — returns `{valid, error?}`
- `mutateTask(task, params)` — applies field changes after validation passes
- `applyMutation(state, index, params)` — combined validate + mutate in one call
- `hasMutableField(params)` — checks if any actionable field is present

### Step 5 — Refactor the original reducer to delegate

The original reducer file becomes a thin orchestrator:

```typescript
// state-reducer.ts — now delegates to focused modules
import { isTransitionValid } from "./transition-validator.js";
import { createTask, cloneTask } from "./task-factory.js";
import { validateUpdateParams, mutateTask } from "./update-mutator.js";

export function reduceState(state: TaskState, action: Action): TaskState {
  switch (action.type) {
    case "CREATE": {
      const newTask = createTask(action.item);
      return { ...state, tasks: [...state.tasks, newTask] };
    }
    case "UPDATE": {
      const idx = state.tasks.findIndex(t => t.id === action.id);
      const validation = validateUpdateParams(state.tasks[idx], action, state);
      if (!validation.valid) return state; // or throw
      const updated = mutateTask(state.tasks[idx], action);
      return { ...state, tasks: state.tasks.map((t, i) => i === idx ? updated : t) };
    }
    // ... other actions delegate similarly
  }
}
```

### Step 6 — Verify

```bash
# Type-check — all imports resolve
npx tsc --noEmit

# Run existing tests — no regressions
npm test

# The original reducer is now thin (under 100 lines ideally)
wc -l path/to/reducer.ts

# Each extracted module is focused (single responsibility)
wc -l path/to/transition-validator.ts
wc -l path/to/task-factory.ts
wc -l path/to/update-mutator.ts
```

## Pitfalls

- **Over-splitting**: If a module has fewer than 30 significant lines of logic, it's probably not worth extracting. Keep it in the reducer until the pattern justifies extraction.
- **Circular dependencies**: After extracting, check for cycles. Common culprit: `update-mutator.ts` imports `transition-validator.ts` and `task-factory.ts`, but don't let those import back from `update-mutator.ts`.
- **Breaking the public API**: If the reducer's exports are consumed by tests or callers, keep the same export surface. Add the deep modules as additional exports, don't remove the originals until callers migrate.
- **Timestamp consistency**: All mutations should set `updatedAt` to the current time. The factory and mutator should handle this — callers should NOT need to pass timestamps.
- **Test coverage**: After extracting, add unit tests for each module independently. Validator tests should be pure (no state needed). Factory tests should check defaults. Mutator tests should verify validated fields are applied and unvalidated fields are rejected.

## Verification

```bash
# TypeScript compiles cleanly
npx tsc --noEmit

# Original reducer file is now focused (ideally <100 lines)
# Each extracted module has a single clear responsibility
# No circular imports between extracted modules

# All existing tests pass
npm test

# New module-level tests exist
ls path/to/test/*-validator*.test.ts
ls path/to/test/*-factory*.test.ts

# The reducer's public API surface is unchanged
grep "^export" path/to/reducer.ts