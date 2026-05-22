---
name: "deepen-monolith-into-submodules"
description: "Deepen any monolithic module by extracting focused submodules for distinct operational concerns (path resolution, config building, process spawning, event handling, I/O operations, audit logging). Use when a TypeScript/Node.js module exceeds 200 lines and mixes 2+ distinct concerns. Adjacent to global:deepen-state-reducer-into-modules (for state reducers) and global:extract-command-router-from-tool-handler (for command routers)."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Deepen a Monolith Into Focused Submodules

## When to Use

Extract focused submodules from any monolithic TypeScript/Node.js module when:

- The module exceeds ~200 lines
- It mixes **2+ distinct operational concerns** (path resolution, config building, process spawning, event classification, I/O, audit logging)
- Unit tests are hard to write because test setup requires the full pipeline
- You need to add new capabilities without bloating the module further
- The same resolution/spawn/config pattern would be reused elsewhere

Do NOT use for:
- Modules under 100 lines with simple logic — let the shape settle first
- Modules already focused on a single concern
- First-time experimentation before the pattern is clear

**Adjacent skills** (check these first if your monolith fits their domain):
- `global:deepen-state-reducer-into-modules` — for state reducers with validation/construction/mutation concerns
- `global:extract-command-router-from-tool-handler` — for tool handlers with subcommand routing

## Procedure

### Step 1 — Analyze the monolith's distinct concerns

Read the entire module and identify every distinct operational concern:

| Domain | What It Does | Extract As |
|--------|-------------|------------|
| **Path resolution** | Discover file paths via `require.resolve`, node_modules walk, or hardcoded fallbacks | `resolver.ts` |
| **Config/Data construction** | Build typed config objects with defaults and validation | `config-builder.ts` |
| **Process/Operation execution** | `child_process.spawn`, HTTP calls, or other I/O-heavy operations | `executor.ts` / `process-spawner.ts` |
| **Event classification** | Define event constants, type literals, and classifier functions | `event-types.ts` |
| **I/O / Audit logging** | Read/write files, append audit trails, format log entries with atomic writes | `audit.ts` / `persistence.ts` |
| **State mutation** | Update task/game/entity state triggered by events | `state-updater.ts` |
| **Validation** | Check preconditions, field requirements, transition rules | `validator.ts` |

**Clue**: If you can name the concern as a noun phrase in a sentence like "the module handles **[concern]**", it's a candidate for extraction.

### Step 2 — Create the subdirectory

Create a subdirectory named after the module's domain:

```bash
mkdir -p path/to/domain/subdir/
```

Example conventions from real code:
- `dispatch/` for dispatch pipeline concerns (resolver, config-builder, process-spawner)
- `intercom/` for intercom event handling (event-types, plan-audit, state-updater)
- `state/` for state management (transition-validator, task-factory, update-mutator)

### Step 3 — Extract each concern into a focused module

For each concern, create a dedicated module with:
- **Typed interfaces** for all public inputs and outputs
- **Pure functions** or minimal I/O surface (inject I/O where possible for testability)
- **One clear responsibility** per file

#### Path resolver pattern

A module that discovers runtime resources with hierarchical fallback:

```typescript
// resolver.ts
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { createRequire } from "node:module";

export interface ResolvedPaths {
  /** Absolute path to the primary resource (e.g. CLI entry point) */
  primary: string;
  /** Absolute path to the secondary resource (e.g. runner script) */
  secondary: string;
  /** Whether both paths resolved successfully */
  resolved: boolean;
  /** Error message if resolution failed */
  error?: string;
}

// Each strategy is a separate function — independently testable
function resolveFromRequire(): string | undefined { /* ... */ }
function resolveFromSibling(): string | undefined { /* ... */ }
function resolveFromHardcoded(): string | undefined { /* ... */ }

export function resolveAllPaths(): ResolvedPaths {
  const candidates = [resolveFromRequire, resolveFromSibling, resolveFromHardcoded];
  let primary: string | undefined;
  let secondary: string | undefined;

  for (const fn of candidates) {
    try {
      primary ??= fn();
    } catch { /* skip */ }
  }
  // ... same for secondary
}
```

**Key decision points**:
- **Fallback strategies**: Try `require.resolve` first, then walk from sibling modules, then hardcoded paths. Different environments may have different node_modules layouts.
- **Caching**: If resolution is called frequently, cache on first call.
- **Error granularity**: Track which resource failed (separate error paths for primary vs secondary).

#### Config builder pattern

Build typed configs from payloads with defaults, validation, and serialization:

```typescript
// config-builder.ts

export interface Config { /* ... */ }
export interface ValidationResult { valid: boolean; error?: string; }
export interface WriteResult { success: boolean; path?: string; error?: string; }

export const DEFAULTS = {
  /* ... */
};

export function buildConfig(payload: Payload): Config {
  return {
    id: payload.runId,
    steps: [{ agent: payload.agent, task: payload.task }],
    // ... apply overrides and defaults
  };
}

export function validateCwd(config: Config): ValidationResult {
  if (!existsSync(config.cwd)) {
    return { valid: false, error: `cwd does not exist: ${config.cwd}` };
  }
  return { valid: true };
}

export function writeConfigToDisk(config: Config): WriteResult {
  try {
    mkdirSync(dirname(config.path), { recursive: true });
    writeFileSync(config.path, JSON.stringify(config, null, 2));
    return { success: true, path: config.path };
  } catch (error) {
    return { success: false, error: `Failed to write config: ${error}` };
  }
}
```

**Key decision points**:
- **I/O injection**: `writeConfigToDisk` uses Node.js `fs` directly. For deeper testability, accept a `writeFile` function parameter.
- **Temp directory**: Use `/tmp/<project>` for ephemeral artifacts. Create with `recursive: true`.
- **Validation vs construction**: Keep validation in config-builder (synchronous, no I/O) and write/save separate.

#### Process spawner / Executor pattern

Encapsulate subprocess creation (or any async operation) with proper lifecycle management:

```typescript
// process-spawner.ts
import { spawn } from "node:child_process";

export interface OperationResult {
  success: boolean;
  pid?: number;
  runId: string;
  error?: string;
  fallbackCommand?: string;
}

export interface SpawnDeps {
  /** Path to the runtime CLI entry point */
  runtimePath: string;
  /** Path to the script to execute */
  scriptPath: string;
  /** Path to config file on disk */
  configPath: string;
  /** Current working directory */
  cwd: string;
}

/** Generate a fallback command for manual execution when automated spawn fails */
export function buildFallbackCommand(payload: Payload): string {
  return `cli-tool --agent ${payload.agent} --task "${payload.task.replace(/"/g, '\\"')}"`;
}

/** Spawn a detached subprocess and return the result */
export function executeOperation(deps: SpawnDeps): OperationResult {
  const proc = spawn(process.execPath, [
    deps.runtimePath, deps.scriptPath, deps.configPath,
  ], {
    cwd: deps.cwd,
    detached: true,     // child survives parent exit
    stdio: "ignore",    // no stdin/stdout/stderr forwarding
    windowsHide: true,
  });

  proc.on("error", (error) => {
    console.error(`spawn error: ${error.message}`);
  });

  if (typeof proc.pid !== "number") {
    return { success: false, runId: deps.configPath, error: "spawn did not produce a PID" };
  }

  proc.unref(); // prevent parent from waiting for child

  return { success: true, pid: proc.pid, runId: deps.configPath };
}
```

**Key decision points**:
- **`detached: true`**: Essential if the child should survive the parent exiting. Omit if children should die with the parent.
- **`stdio: "ignore"`**: Prevents file descriptor leaks from background processes. Use `"pipe"` only if capturing output.
- **`proc.unref()`**: Allows the Node.js process to exit without waiting for the child. Without it, the parent stays alive.
- **Fallback command**: Always provide a manual CLI command as a fallback — runtime lookups can fail.

#### Event classifier pattern

Standardize event type constants, raw event shapes, and a classifier function:

```typescript
// event-types.ts

/** Canonical event types as const object for compile-time safety */
export const EventType = {
  NEEDS_ATTENTION: "needs_attention",
  ACTIVE_LONG_RUNNING: "active_long_running",
  COMPLETED: "completed",
  FAILED: "failed",
  IDLE: "idle",
} as const;

export type EventTypeValue = (typeof EventType)[keyof typeof EventType];

/** Raw event shape (from an external source like intercom or webhook) */
export interface RawEvent {
  agent: string;
  runId: string;
  index?: number;
  "-type"?: string;
  reason?: string;
  message?: string;
}

/** Classified event with resolved/enriched fields */
export interface ClassifiedEvent {
  type: EventTypeValue | "unknown";
  taskId: number;
  agent: string;
  message: string;
  runId: string;
}

/** Classify a raw event — returns null if the event can't be tracked */
export function classifyEvent(raw: RawEvent, lookupFn: Lookup): ClassifiedEvent | null {
  if (!raw.runId) return null;
  const task = lookupFn(raw.runId);
  if (!task) return null;
  const type = (raw["-type"] ?? raw.reason ?? "unknown") as EventTypeValue | "unknown";
  return { type, taskId: task.id, agent: raw.agent, message: raw.message ?? "", runId: raw.runId };
}
```

**Key decision points**:
- **`event.type` vs `event.reason`**: pi-subagents may use different fields (`-type` vs `reason`). The classifier should normalize these.
- **Return null for untracked events**: Events for unknown runIds should be silently ignored, not crash.
- **Const objects vs enums**: Use `as const` objects for string literal types — they compile to plain JS and are safe for serialization.

#### Audit log pattern

Append structured entries to files with atomic writes:

```typescript
// audit.ts
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export interface AuditResult { success: boolean; path?: string; }

function atomicWrite(path: string, data: string): void {
  const tmpPath = path + ".tmp";
  writeFileSync(tmpPath, data, "utf-8");
  renameSync(tmpPath, path); // atomic on same filesystem
}

export function formatEntry(emoji: string, agent: string, message: string): string {
  const timestamp = new Date().toISOString().slice(0, 16).replace("T", " ");
  return `- **[${timestamp}]** ${emoji} ${agent}: ${message}`;
}

export function appendLog(filePath: string, entry: string): AuditResult {
  if (!existsSync(filePath)) return { success: false };
  const content = readFileSync(filePath, "utf-8");
  atomicWrite(filePath, `${content}\n${entry}`);
  return { success: true, path: filePath };
}
```

**Key decision points**:
- **Atomic writes**: Write to `.tmp` file then `renameSync` to prevent partial writes from crashes.
- **Timestamp format**: Consistent, sortable ISO format without timezone for readability.
- **Sentinel markers**: Use known marker strings (like `"## Closeout"`) to detect completion in polling.
- **Directory creation**: Ensure parent directory exists with `mkdirSync(dir, { recursive: true })`.

### Step 4 — Refactor the original file into a thin facade

The original file becomes a thin re-export facade that imports from the extracted modules:

```typescript
// original.ts — now a thin facade for backward compatibility

// Re-export public API from extracted modules
export { executeOperation, type OperationResult } from "./subdir/process-spawner.js";
export { resolveAllPaths, type ResolvedPaths } from "./subdir/resolver.js";
export { buildConfig, writeConfigToDisk, validateCwd } from "./subdir/config-builder.js";
```

This preserves backward compatibility — all existing imports (`import { executeOperation } from "./original.js"`) continue to work without changes.

### Step 5 — Create an orchestrator (optional)

If there's a common workflow that composes the extracted modules, add a compose function to one of them or to a new `index.ts`:

```typescript
// In process-spawner.ts (or a new index.ts)
import { resolveAllPaths } from "./resolver.js";
import { buildConfig, writeConfigToDisk, validateCwd } from "./config-builder.js";
import { buildFallbackCommand, executeOperation } from "./process-spawner.js";

/**
 * Execute the full workflow: resolve paths → build config → write config → spawn.
 * Composes the three extracted modules into a single call.
 */
export function executeWorkflow(payload: Payload): OperationResult {
  // Step 1: Resolve runtime paths
  const paths = resolveAllPaths();
  if (!paths.resolved) {
    return { success: false, runId: payload.runId, error: paths.error, fallbackCommand: buildFallbackCommand(payload) };
  }

  // Step 2: Build and validate config
  const config = buildConfig(payload);
  const cwdCheck = validateCwd(config);
  if (!cwdCheck.valid) {
    return { success: false, runId: payload.runId, error: cwdCheck.error, fallbackCommand: buildFallbackCommand(payload) };
  }

  // Step 3: Write config to disk
  const writeResult = writeConfigToDisk(config);
  if (!writeResult.success) {
    return { success: false, runId: payload.runId, error: writeResult.error, fallbackCommand: buildFallbackCommand(payload) };
  }

  // Step 4: Spawn subprocess
  return executeOperation({
    runtimePath: paths.primary,
    scriptPath: paths.secondary,
    configPath: writeResult.path!,
    cwd: config.cwd,
  });
}
```

**When to add an orchestrator**:
- The extracted modules are always called together in the same sequence
- Callers would otherwise need to repeat the same 3-4 calls
- The compose reduces the public API surface (one call instead of many)

**When NOT to add an orchestrator**:
- Callers may use the extracted modules independently
- The composition logic adds coupling you want to avoid
- Different callers compose in different ways

### Step 6 — Verify

```bash
# TypeScript compiles cleanly — no new type errors
npx tsc --noEmit

# Original file is now thin (<30 lines ideally — just re-exports)
wc -l path/to/original.ts

# Each extracted module is independently testable (pure functions, small file size)
wc -l path/to/subdir/*.ts

# Public API surface is unchanged — all original exports still present
grep "^export" path/to/original.ts

# No circular dependencies between extracted modules
npx madge --circular path/to/subdir/ 2>/dev/null || echo "check manually"
```

## Pitfalls

- **Over-splitting**: If an extracted module has fewer than 30 significant lines (excluding imports and type definitions), it's not worth extracting. Keep it in the monolith until the pattern justifies the split.

- **Circular dependencies**: Extracted modules must NOT import each other in cycles. Common safe chain: `resolver ← config-builder ← process-spawner` (config-builder imports from resolver, process-spawner imports from both). Never let `process-spawner → index.ts → process-spawner`.

- **Breaking the public API**: The facade must re-export EVERYTHING the original exported. Check all consumers before removing any export. Run `grep "from.*original"` across the codebase to find importers.

- **Inconsistent error signaling**: Choose ONE error pattern — either result objects like `{ success: boolean, error?: string }` or thrown exceptions. Don't mix sentinel strings in some modules and exceptions in others.

- **Orphan processes**: When extracting process spawn logic, always use `detached: true` + `proc.unref()`. Without `detached`, children die when parent exits. Without `unref()`, the parent stays alive waiting for children.

- **Missing fallback commands**: Runtime path resolution (jiti, node_modules) can fail in different environments. Always provide a manual CLI fallback command string so operators can execute the operation themselves.

- **Config staleness**: Every invocation must write a fresh config file with a unique ID. Never reuse stale config JSON from `/tmp` — it may reference stale paths, stale PIDs, or stale task contexts.

- **File descriptor leaks**: Background processes with `stdio: "pipe"` hold open pipes to the parent. Use `stdio: "ignore"` for fully detached processes that don't need I/O.

- **Atomic write safety**: WriteFileSync to a temporary `.tmp` path then `renameSync` to the target path. This prevents partial/corrupt files if the process crashes mid-write. Always call `renameSync` (synchronous) — async rename could interleave.

- **Accidental timestamp collisions**: In tests, back-to-back calls to `new Date().toISOString()` can produce the same millisecond. If timestamps are used as keys, add a counter or UUID suffix.

## Verification

```bash
# 1. TypeScript compiles cleanly
npx tsc --noEmit

# 2. Original file is now under 50 lines (ideally just re-exports)
wc -l path/to/original.ts

# 3. Each extracted module has a clear responsibility
#    (name reflects its concern — resolver, config-builder, etc.)
wc -l path/to/subdir/*.ts

# 4. No circular imports between extracted modules
egrep "^import.*from.*\.\./subdir/" path/to/subdir/*.ts | grep -v "\.\./subdir/"

# 5. Public API surface is unchanged
grep "^export" path/to/original.ts

# 6. All existing imports still resolve
#    Check that no import of the original module errors
for f in $(grep -rl "from.*original" . --include="*.ts"); do
  echo "Consumer: $f"
done

# 7. Each extracted module can be unit-tested independently
#    (pure functions in resolver, config-builder; mocked I/O in process-spawner)
```

## Real-World Examples

This skill was extracted from a systematic refactoring session on a clanker-ops extension where three monolithic modules were deepened in sequence:

| Monolith | Subdirectory | Extracted Modules |
|----------|-------------|-------------------|
| `background-spawner.ts` (415 lines → 18 lines) | `dispatch/` | `resolver.ts` — path resolution (jiti CLI + runner script), `config-builder.ts` — config construction + validation + disk write, `process-spawner.ts` — subprocess spawn + fallback command |
| `intercom-handler.ts` (371 lines → 15 lines) | `intercom/` | `event-types.ts` — event constants + classifier, `plan-audit.ts` — plan file audit trail I/O, `state-updater.ts` — state mutations triggered by events |
| `state-reducer.ts` (317 lines → thin) | `state/` | `transition-validator.ts` — valid state transitions, `task-factory.ts` — task creation with defaults, `update-mutator.ts` — field-level mutation with validation |