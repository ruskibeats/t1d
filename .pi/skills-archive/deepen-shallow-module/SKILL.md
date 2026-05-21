---
name: "deepen-shallow-module"
description: "Apply the improve-codebase-architecture \"deepening\" pattern: decompose a shallow module (god class) into focused modules (Repository, Validator, Factory, Mutator, Presenter). Use when a module has multiple concerns, large surface area, or is hard to test due to mixed responsibilities."
version: 4
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

- A module has 300+ lines and mixes data access, validation, creation, and mutation
- You need to unit-test business logic without mocking file I/O
- The improve-codebase-architecture skill identified a "shallow module" opportunity
- Multiple unrelated `import` groups in a single file suggest mixed concerns

## Procedure
### 1. Create CONTEXT.md first (if missing)
- Write domain glossary: core concepts, status values, state transitions, metadata fields
- Reference the existing codebase terms — this anchors the language for extracted modules

### 2. Identify shallow modules via code review
Look for modules that mix these concerns under one file. Two common decomposition families:

**State/Data management concerns:**
- **Data access** (file I/O, DB reads/writes) — extract as `*Repository`
- **State transition rules** (valid transitions, invariants) — extract as `*Validator`
- **Object creation** (constructors, defaults, ID generation) — extract as `*Factory`
- **Field mutations** (update, patch, merge logic) — extract as `*Mutator`
- **Presentation logic** (formatting, grouping for display) — extract as `*Presenter`

**Process pipeline concerns** (e.g., background dispatch, batch processing, multi-stage workflows):
- **Path/Resource resolution** (traversing node_modules, finding scripts, locating files) — extract as `*Resolver`
- **Configuration/Input assembly** (building config objects, writing temp files) — extract as `*ConfigBuilder`
- **Process orchestration** (spawning, lifecycle management, error handling, fallback commands) — extract as `*ProcessSpawner`

If a module has a mix of resource discovery, config construction, and execution orchestration, it's a process pipeline candidate. Extract each pipeline stage into its own leaf module.

### 3. Extract each concern (one per file)
```typescript
// State/Data pattern
// state/task-repository.ts — File I/O only
export class TaskRepository {
  readState(): TaskState { ... }
  writeState(state: TaskState): void { ... }
}

// state/transition-validator.ts — Transition rules only
export class TransitionValidator {
  canTransition(from: Status, to: Status): boolean { ... }
}

// state/task-factory.ts — Object creation only
export class TaskFactory {
  create(params: CreateParams): Task { ... }
}

// Process pipeline pattern
// dispatch/resolver.ts — Path resolution only
export class Resolver {
  resolveCliPath(): string { ... }
  resolveRunnerScript(): string { ... }
}

// dispatch/config-builder.ts — Config assembly only (pure function)
export function buildDispatchConfig(payload: DispatchPayload): RunnerConfig { ... }

// dispatch/process-spawner.ts — Process lifecycle only
export class ProcessSpawner {
  spawn(config: RunnerConfig): ChildProcess { ... }
}
```

### 4. Update the original module to import from new modules
Replace inline logic with delegation:
```typescript
// Before: inline transition check + inline path resolution + inline spawn
if (isTransitionValid(from, to)) { ... }
const cliPath = findJitiCli();  // mixed with other concerns
const proc = spawn(cliPath, args);  // mixed with error handling

// After: delegate to extracted modules
const validator = new TransitionValidator();
if (validator.canTransition(from, to)) { ... }

const resolver = new Resolver();
const builder = new ConfigBuilder();
const spawner = new ProcessSpawner();
const config = builder.build(payload);
spawner.spawn(config);
```

### 5. Keep original module as thin facade (if backward compatibility needed)
Re-export public APIs from the original location so existing importers don't break:
```typescript
// background-spawner.ts — Thin facade after deepening
export { Resolver } from "./dispatch/resolver.js";
export { buildDispatchConfig } from "./dispatch/config-builder.js";
export { ProcessSpawner } from "./dispatch/process-spawner.js";
```

### 6. Verify compilation
```bash
npx tsc --noEmit  # or ./node_modules/.bin/tsc --noEmit
```

### 7. Commit with descriptive message
```bash
git add <files>
git commit -m "clanker-ops: deepen <original-module> into dispatch/resolver, dispatch/config-builder, dispatch/process-spawner"
```
## Pitfalls
- **Circular imports**: Extracted modules should import from the original module's types, not from each other. Keep type definitions in the original `types.ts` if possible.
- **Over-extraction**: Don't extract a module for a single 3-line function. Only extract when the concern has enough surface area (multiple methods, distinct lifecycle, or testable behavior).
- **Brittle interface**: Keep extracted module interfaces minimal. `Repository` should expose 2-3 methods (`read`, `write`, `exists`), not the entire public surface of the original.
- **Missing exports**: After refactoring, update re-exports to include new modules for backward compatibility.
- **Test gaps**: Each extracted module should be independently testable. Create a `MemoryRepository` variant for tests that don't need file I/O.
- **Process pipeline: leaked subprocesses**: When extracting a `ProcessSpawner`, ensure it handles `'error'` and `'exit'` events and provides a `kill()` method or disposal mechanism. Otherwise, orphaned child processes can accumulate.
- **Process pipeline: temp file cleanup**: A `ConfigBuilder` that writes temp config files must clean them up after spawn completes. Use `after`/`finally` blocks or register cleanup — temp files in `/tmp` that accumulate across runs can waste disk space.
- **Process pipeline: fragile path resolution**: A `Resolver` that traverses `node_modules` with relative paths (`../../`) is brittle. Anchor path resolution from `import.meta.url` or `__dirname` of the runner script, not from the extension's working directory. Verify paths resolve correctly when the extension is installed globally vs. locally.
- **Process pipeline: error boundary ambiguity**: When a pipeline has three stages (resolve → build → spawn), decide which stage owns error handling. The spawner should own process-level errors (exit codes, signals). The config builder should own validation errors (missing fields, type mismatches). Don't let one stage swallow another's errors.
- **Process pipeline: missing `import type` for type-only imports**: When extracting dispatch modules, the config builder and resolver often only reference types from the original module. Use `import type { ... }` to avoid runtime circular dependencies.
## Verification
- [ ] `npx tsc --noEmit` passes with zero errors
- [ ] Original module compiles using `import` from new extracted modules
- [ ] Each extracted module has a single, focused responsibility
- [ ] No circular imports between extracted modules
- [ ] New modules are visible in `git status` and committed
- [ ] CONTEXT.md exists with domain glossary
- [ ] **Process pipeline**: each pipeline stage (Resolver, ConfigBuilder, ProcessSpawner) is independently testable — Resolver doesn't spawn, ConfigBuilder doesn't write to disk unless necessary, ProcessSpawner accepts injected config
- [ ] **Process pipeline**: temp files written by ConfigBuilder are cleaned up after spawn completes (or are small enough to be harmless)
- [ ] **Process pipeline**: Resolver paths work both when installed globally (`npm install -g`) and locally (`node_modules/.bin`)
- [ ] **Process pipeline**: ProcessSpawner handles `error` and `exit` events and provides a `kill()` method for cleanup