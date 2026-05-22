---
name: "clanker-ops-background-dispatch"
description: "Background dispatch of Clanker Ops tasks to pi-subagents using detached subprocess spawning. Covers path resolution, config building, disk-based runner config, process spawn with fallback commands, and persistent audit logging."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Clanker Ops Background Dispatch

Background-dispatch Clanker Ops tasks to pi-subagents via detached subprocess. The flow: resolve jiti + runner paths → build pi-subagents RunnerConfig → write config JSON to /tmp → spawn detached Node.js process → write fallback command for manual execution → log to persistent audit trail.

## When to Use

- `/clanker dispatch #N to @agent` is called and you need to spawn a background pi-subagent.
- A task needs to run asynchronously while the controller session remains responsive.
- You want a persistent audit trail (`.pi/dispatch-log.json`) and plan file entries per dispatch.

## Architecture

```
DispatchPayload → resolvePaths() → buildRunnerConfig() → writeConfigToDisk() → spawnBackgroundProcess() → audit log
                                                                          ↓
                                                                    fallbackCommand (manual)
```

Modules (under `.pi/extensions/clanker-ops/`):

| File | Role |
|------|------|
| `dispatch.ts` | Payload assembly, plan section extraction |
| `dispatch/resolver.ts` | Resolve jiti CLI + pi-subagents runner paths |
| `dispatch/config-builder.ts` | Build + write RunnerConfig JSON |
| `dispatch/process-spawner.ts` | Subprocess spawn + fallback command |
| `dispatch/dispatch-log.ts` | Persistent audit log (atomic writes) |
| `dispatch/plan-generator.ts` | Auto-generate plan files from task + agent |
| `background-spawner.ts` | Thin facade re-exporting the dispatch pipeline |

## Procedure

### 1. Resolve Runtime Paths

Call `resolveAllPaths()` from `dispatch/resolver.ts`. It tries three strategies:
1. `require.resolve("jiti/package.json")` then look for bin field
2. Walk from `pi-subagents/package.json` dir to sibling `jiti/package.json`
3. Hardcoded fallback: `/root/.pi/agent/npm/node_modules/pi-subagents/package.json`

Same multi-strategy for the runner script (`subagent-runner.ts`).

```typescript
const paths = resolveAllPaths();
if (!paths.resolved) {
  // Fall back to manual command
  return buildFallbackCommand(payload);
}
// paths.jiti, paths.runner
```

**Pitfall**: jiti or runner resolution can fail if node_modules layout changes. Always provide a fallback.

### 2. Build Runner Config

Call `buildRunnerConfig(payload)` from `dispatch/config-builder.ts`. This creates the full `RunnerConfig` object:

```typescript
const config = buildRunnerConfig(payload);
// Steps: [{ agent: payload.agent, task: payload.task, cwd, skills, maxSubagentDepth }]
// resultPath: /tmp/clanker-dispatch/result-{runId}.json
// controlConfig: { enabled, needsAttentionAfterMs, activeNoticeAfterMs, ... }
// controlIntercomTarget, childIntercomTargets
```

Write to disk: `writeConfigToDisk(config)` → `/tmp/clanker-dispatch/config-{runId}.json`

### 3. Build Fallback Command

If path resolution or spawn fails, provide a manual fallback:

```typescript
`subagent single --agent ${agent} --async true --output ${outputPath} --task "..."`
```

### 4. Spawn Background Process

Use `child_process.spawn` with the Node.js executable:

```typescript
const proc = spawn(process.execPath, [jitiPath, runnerPath, configPath], {
  cwd: process.cwd(),
  detached: true,
  stdio: "ignore",
  windowsHide: true,
});
proc.unref(); // Allow parent to exit independently
```

Key choices:
- `detached: true` — child survives parent exit
- `stdio: "ignore"` — no stdin/stdout/stderr forwarding
- `proc.unref()` — prevent parent from waiting
- `spawn` (not `exec`) — no buffer limits on large config/output

### 5. Persist Audit Entry

Log the dispatch to `.pi/dispatch-log.json`:

```typescript
logDispatch({
  taskId,
  agent,
  runId,
  status: "dispatched",  // or "running"/"completed"/"failed"
  pid: proc.pid,
  outputPath,
});
```

### 6. Handle Lifecycle Events (Intercom)

Pi-subagents emit intercom control events. Handle them in the event classifier:

| Event Type | State Update | Audit Entry |
|---|---|---|
| `needs_attention` | metadata.lastAlert | ⚠️ heartbeat |
| `active_long_running` | metadata.lastHeartbeat | ⏱️ heartbeat |
| `completion_guard` / `failed` | status="failed" | ❌ |
| (artifact poll) | status="completed" | ✅ COMPLETED |

See `intercom/event-types.ts`, `intercom/state-updater.ts`, and `intercom/plan-audit.ts` for the handler pipeline.

### 7. Artifact Polling (Session Restart)

On session start, poll in_progress tasks for completed dispatch output files:

```typescript
// In intercom/state-updater.ts
pollDispatchArtifacts(): void {
  for each in_progress task with outputPath + dispatchRunId:
    if outputPath contains "## Closeout" or "## Audit Report":
      mark task completed, append "✅ COMPLETED" to plan log
}
```

## Key Types

```typescript
interface DispatchPayload {
  taskId: number;
  runId: string;
  agent: string;
  agentFilePath: string;
  task: string;
  planPath: string;
  outputPath: string;
  controlIntercomTarget: string;
}

interface RunnerConfig {
  id: string;
  steps: Array<{ agent: string; task: string; cwd: string; skills: string[]; maxSubagentDepth: number }>;
  resultPath: string;
  cwd: string;
  controlConfig: { ... };
  controlIntercomTarget: string;
  childIntercomTargets: string[];
  // ... piPackageRoot, piArgv1, asyncDir, etc.
}

interface SpawnResult {
  autoSpawned: boolean;
  pid?: number;
  runId: string;
  error?: string;
  fallbackCommand?: string;
}
```

## Pitfalls

1. **jiti resolution fails** → Always check `resolved` boolean and provide `buildFallbackCommand()`.
2. **orphan processes** → `detached: true` + `unref()` means children become orphans if the parent crashes. Use `/tmp/clanker-dispatch/` artifacts for recovery.
3. **Config JSON staleness** → Write a fresh config every dispatch (don't reuse stale files).
4. **Intercom events lost on restart** → Always call `pollDispatchArtifacts()` on session start to catch up.
5. **Atomicity** → `dispatch-log.json` writes go to `.tmp` then `renameSync` to avoid partial writes.
6. **Plan file race** → If plan-generator writes a plan while the intercom handler appends to it, both use `readFileSync` + `writeFileSync` which is safe in single-process Node.js but unsafe across processes.

## Verification

- [ ] `resolveAllPaths()` returns `resolved: true` with valid jiti and runner paths
- [ ] `buildRunnerConfig(payload)` produces valid RunnerConfig JSON
- [ ] `writeConfigToDisk(config)` writes config to `/tmp/clanker-dispatch/config-{runId}.json`
- [ ] `spawnBackgroundProcess(deps)` returns `autoSpawned: true` with a valid pid
- [ ] `buildFallbackCommand(payload)` produces a valid subagent CLI command
- [ ] `logDispatch(entry)` appends to `.pi/dispatch-log.json` with atomic write (temp → rename)
- [ ] Intercom handler `handleIntercomEvent(event)` correctly classifies and applies state mutations
- [ ] `pollDispatchArtifacts()` catches completed tasks on session restart