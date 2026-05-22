---
name: "deepen-clanker-ops-pipeline-modules"
description: "Deepen monolithic Clanker Ops pipeline modules (background-spawner, intercom-handler) by extracting focused submodules for resolver, config-builder, process-spawner, plan-generator, dispatch-log, event-types, plan-audit, and state-updater. Use when a Clanker Ops pipeline module exceeds ~200 lines and mixes 3+ distinct responsibilities."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Deepen Clanker Ops Pipeline Modules

## When to Use

Deepen monolithic Clanker Ops pipeline modules by extracting focused submodules. Use when:

- A pipeline module (background spawner, intercom handler) exceeds ~200 lines
- The module mixes 3+ distinct concerns (path resolution, config building, process spawning, logging, event classification, audit trailing, state updating)
- You need to test individual pipeline stages independently
- A new subagent type or dispatch mode requires different config/spawn logic
- Debugging dispatch failures requires isolating which stage failed (resolution, config write, spawn)

Triggers: "deepen clanker-ops", "refactor background spawner", "extract dispatch modules", "deepen intercom handler", "refactor clanker-ops pipeline"

Do NOT use for:
- State reducer deepening (use `global:deepen-state-reducer-into-modules` instead)
- Navigation/understanding (use `project:t1d:navigate-clanker-ops` instead)
- Modules under 100 lines with simple logic
- First-time experimentation — let the pipeline shape settle before extracting

## Architecture Context

Clanker Ops pipeline modules follow a lifecycle pattern:

```
entry point → resolver → config builder → spawner → logger
                                       ↕
                                    plan generator

entry point → event classifier → plan auditor → state updater
```

The two main pipeline modules to deepen:

### 1. Dispatch Pipeline (background-spawner → dispatch/)

| Original | Extracted Modules | Concern |
|----------|------------------|---------|
| Path resolution | `dispatch/resolver.ts` | Find jiti CLI, pi-subagents runner from node_modules |
| Config building | `dispatch/config-builder.ts` | Map DispatchPayload → RunnerConfig JSON |
| Process spawning | `dispatch/process-spawner.ts` | `child_process.spawn` with detached, unref |
| Plan generation | `dispatch/plan-generator.ts` | Auto-generate `.pi/todo-plans/#N_plan.md` |
| Audit logging | `dispatch/dispatch-log.ts` | Persistent `.pi/dispatch-log.json` with read/write/query |
| Orchestration | stays in `dispatch.ts` | `assembleDispatch()` and `executeBackgroundDispatch()` |

### 2. Intercom Handler Pipeline (intercom-handler → intercom/)

| Original | Extracted Modules | Concern |
|----------|------------------|---------|
| Event classification | `intercom/event-types.ts` | ControlEvent shape, classifier, task lookup by runId |
| Plan audit | `intercom/plan-audit.ts` | Append audit entries to plan files |
| State updates | `intercom/state-updater.ts` | Task status mutations + artifact polling from subagent events |
| Orchestration | stays in `intercom-handler.ts` | `handleIntercomEvent()` → classify → audit → update |

## Procedure

### Step 1 — Analyze the monolith's responsibilities

Read the entire pipeline module. Classify every function into a concern domain:

| Domain | Example Functions | Extract as |
|--------|------------------|------------|
| **Path Resolution** | `findJitiPath()`, `resolveRunnerPath()`, `findPiSubagents()` | `dispatch/resolver.ts` |
| **Config Building** | `buildRunnerConfig()`, `writeConfigToDisk()`, `validateCwd()` | `dispatch/config-builder.ts` |
| **Process Spawning** | `spawnBackgroundProcess()`, `buildFallbackCommand()` | `dispatch/process-spawner.ts` |
| **Plan Generation** | `generatePlan()`, `planExists()`, `buildPlanContent()` | `dispatch/plan-generator.ts` |
| **Audit Logging** | `logDispatch()`, `logHeartbeat()`, `logCompletion()`, `getDispatchHistory()` | `dispatch/dispatch-log.ts` |
| **Event Classification** | `classifyEvent()`, `findTaskByRunId()` | `intercom/event-types.ts` |
| **Plan Audit** | `appendAuditEntry()` | `intercom/plan-audit.ts` |
| **State Updates** | `handleIntercomEvent()`, `updateTaskStatus()`, `pollArtifacts()` | `intercom/state-updater.ts` |

### Step 2 — Extract the resolver module

Create a module that encapsulates all path resolution logic. This is the first stage of the dispatch pipeline — config building and spawning depend on the resolved paths.

```typescript
/**
 * Resolver — Resolves jiti CLI and pi-subagents runner script paths.
 * Caches results to avoid repeated filesystem lookups.
 */

import { existsSync } from "node:fs";
import { join } from "node:path";

export interface ResolvedPaths {
  resolved: boolean;
  jiti?: string;
  runner?: string;
  error?: string;
}

export function resolveAllPaths(): ResolvedPaths {
  // Try resolution from several locations (prefer local node_modules)
  const candidates = [
    join(process.cwd(), "node_modules"),
    // other fallback locations
  ];

  for (const base of candidates) {
    const jitiPath = join(base, ".pnpm", /* ... jiti resolution ... */);
    if (existsSync(jitiPath)) {
      const runnerPath = resolvePiSubagentsRunner(base);
      if (runnerPath) {
        return { resolved: true, jiti: jitiPath, runner: runnerPath };
      }
    }
  }

  return { resolved: false, error: "Could not resolve jiti CLI" };
}
```

**Key decisions**:
- Resolution order: node_modules → global → process.argv[1] relative
- Cache resolved paths in a module-level variable to avoid repeated scans
- Return a discriminated result type (`resolved: true | false` + optional error)

### Step 3 — Extract the config builder

Pure function that maps a DispatchPayload into the pi-subagents RunnerConfig:

```typescript
export function buildRunnerConfig(payload: DispatchPayload): RunnerConfig {
  return {
    id: payload.runId,
    steps: [{
      agent: payload.agent,
      task: payload.task,
      cwd: process.cwd(),
      skills: [],
      maxSubagentDepth: 2,
    }],
    resultPath: join("/tmp/clanker-dispatch", `result-${payload.runId}.json`),
    controlConfig: { ...DEFAULT_CONTROL_CONFIG },
    controlIntercomTarget: payload.controlIntercomTarget,
    // ... more fields
  };
}
```

**Config structure** (pi-subagents RunnerConfig):
- `id` — unique run identifier
- `steps` — array of {agent, task, cwd, skills, maxSubagentDepth}
- `resultPath` — where results get written
- `controlConfig` — event notification settings (needsAttentionAfterMs, activeNoticeAfterMs, notifyOn, notifyChannels)
- `controlIntercomTarget` — intercom session name for lifecycle events
- `artifactsDir`, `asyncDir`, `sessionId` — runtime artifacts

Also include serialization:
```typescript
export function writeConfigToDisk(config: RunnerConfig): WriteConfigResult {
  // Writes to /tmp/clanker-dispatch/config-{id}.json
  // Uses atomic write (write tmp file, then rename)
}
```

### Step 4 — Extract the process spawner

Encapsulate child_process.spawn invocation with error handling and fallback:

```typescript
export function spawnBackgroundProcess(deps: SpawnDeps): SpawnResult {
  const proc = spawn(process.execPath, [deps.jitiPath, deps.runnerPath, deps.configPath], {
    cwd: deps.cwd,
    detached: true,    // Must be detached for background execution
    stdio: "ignore",   // Don't inherit stdio — background process
    windowsHide: true,
  });

  proc.on("error", (error) => {
    console.error(`[clanker-ops] spawn error: ${error.message}`);
  });

  if (typeof proc.pid !== "number") {
    return { autoSpawned: false, runId: deps.configPath, error: "No PID" };
  }

  proc.unref();  // Allow parent to exit independently
  return { autoSpawned: true, pid: proc.pid, runId: deps.configPath };
}
```

Also provide a fallback command string for when auto-spawn fails:

```typescript
export function buildFallbackCommand(payload: DispatchPayload): string {
  return `subagent single --agent ${payload.agent} --async true ...`;
}
```

**Pitfall**: `proc.unref()` is essential — without it, the parent process won't exit until the child does. This is the key that makes the spawn truly "background".

### Step 5 — Extract the plan generator

```typescript
export function generatePlan(input: GeneratePlanInput): GeneratePlanResult {
  // Reads agent definition + task description
  // Writes .pi/todo-plans/#{taskId}_plan.md
  // Sections: Intended Outcome, Step-by-Step, Verification, Dependencies, Audit
}
```

**Plan structure**:
- `Intended Outcome` — from task description or agent role
- `Step-by-Step` — generic steps based on agent role
- `Verification` — checklist with default items
- `Dependencies` — from task.blockedBy
- `Audit` — timestamped event table

### Step 6 — Extract the dispatch log

Persistent JSON log at `.pi/dispatch-log.json`:

```typescript
export function logDispatch(entry: DispatchEntry): void;
export function logHeartbeat(taskId: number, runId: string): void;
export function logCompletion(taskId: number, runId: string, status: "completed" | "failed", error?: string): void;
export function getDispatchHistory(limit = 20): DispatchEntry[];
export function formatDispatchHistory(limit = 20): string;
```

**File format**: Simple JSON array of DispatchEntry objects. Use atomic writes (write .tmp, rename) to prevent corruption.

### Step 7 — Extract intercom event types

```typescript
export const EventType = {
  NEEDS_ATTENTION: "needs_attention",
  ACTIVE_LONG_RUNNING: "active_long_running",
  COMPLETION_GUARD: "completion_guard",
  FAILED: "failed",
} as const;
```

Include classifier:
```typescript
export function classifyEvent(event: ControlEventLike): ClassifiedEvent | null {
  // Extract runId, taskId, message from raw event
  // Map event type to canonical EventType
  // Return null if event can't be classified (e.g., no runId)
}
```

**Pitfall**: Event classification must handle the `-type` TypeScript trap — use `"-type"?: string` not `type?: string` in the interface since `type` is a reserved word in TypeScript type annotations.

### Step 8 — Compose the orchestrator

The original entry point becomes a thin orchestrator that composes the extracted modules:

```typescript
// dispatch.ts — orchestrator
import { resolveAllPaths } from "./dispatch/resolver.js";
import { buildRunnerConfig, writeConfigToDisk } from "./dispatch/config-builder.js";
import { spawnBackgroundProcess, buildFallbackCommand } from "./dispatch/process-spawner.js";
import { logDispatch } from "./dispatch/dispatch-log.js";

export function executeBackgroundDispatch(payload: DispatchPayload): SpawnResult {
  const paths = resolveAllPaths();
  if (!paths.resolved) {
    return { autoSpawned: false, runId: payload.runId, error: paths.error, fallbackCommand: buildFallbackCommand(payload) };
  }

  const config = buildRunnerConfig(payload);
  const writeResult = writeConfigToDisk(config);
  if (!writeResult.success) {
    return { autoSpawned: false, runId: payload.runId, error: writeResult.error, fallbackCommand: buildFallbackCommand(payload) };
  }

  const result = spawnBackgroundProcess({ jitiPath: paths.jiti!, runnerPath: paths.runner!, configPath: writeResult.path!, cwd: process.cwd() });
  logDispatch({ taskId: payload.taskId, agent: payload.agent, runId: payload.runId, status: result.autoSpawned ? "dispatched" : "failed", pid: result.pid });
  return result;
}
```

### Step 9 — Verify

```bash
# Type-check — all imports resolve
npx tsc --noEmit

# Run existing tests — no regressions
npm test

# Each extracted module is focused
wc -l dispatch/resolver.ts
wc -l dispatch/config-builder.ts
wc -l dispatch/process-spawner.ts
wc -l dispatch/plan-generator.ts
wc -l dispatch/dispatch-log.ts
# Each should be <200 lines with single responsibility

# The original file is now thin (orchestrator only)
wc -l dispatch.ts

# Same for intercom modules
wc -l intercom/event-types.ts
wc -l intercom/plan-audit.ts
wc -l intercom/state-updater.ts
wc -l intercom-handler.ts  # should be thin now
```

## Pitfalls

- **Spawn pitfalls**: `detached: true` with `proc.unref()` is mandatory for background execution. Without `detached: true`, the child process is tied to the parent's process group. Without `unref()`, Node.js won't exit until the child does. Use `stdio: "ignore"` to avoid inheriting parent's stdio (which would keep pipes open).
- **PID may be undefined**: `proc.pid` can be `undefined` if spawn fails or exits before Node reads the property. Always check `typeof proc.pid !== "number"` not `if (!proc.pid)`.
- **Config format is pi-subagents-specific**: The RunnerConfig shape (steps, controlConfig, intercomTargets) comes from the pi-subagents runner contract. If pi-subagents changes its config format, update `config-builder.ts`. Don't hardcode paths — resolve them.
- **Dispatch log atomic writes**: Always write to a `.tmp` file then `renameSync()` to the real path. Direct writes risk data loss if the process crashes mid-write.
- **Event type field naming**: In TypeScript interfaces, use `"-type"?: string` for the event type discriminator because `type` is a reserved word. The pi-subagents control event uses `-type` as the discriminator key.
- **Orchestrator should not import every module at module load**: Some modules (plan-generator, dispatch-log) are only needed during dispatch, not at import time. Use lazy imports or keep the orchestrator thin and only import what `assembleDispatch()` needs.

## Verification

- [ ] All dispatch modules have single responsibility and are independently testable
- [ ] `spawnBackgroundProcess` uses `detached: true` + `unref()` + `stdio: "ignore"`
- [ ] Fallback command is produced when auto-spawn fails (resolver, config write, or spawn itself)
- [ ] Dispatch log uses atomic writes (`.tmp` → `rename`)
- [ ] Intercom event classifier handles `"-type"` field correctly
- [ ] Plan generator writes valid markdown with all required sections
- [ ] Config builder produces a valid RunnerConfig JSON
- [ ] TypeScript compiles cleanly (`npx tsc --noEmit`)
- [ ] All existing tests pass
- [ ] The original module file is now under 100 lines (pure orchestrator)