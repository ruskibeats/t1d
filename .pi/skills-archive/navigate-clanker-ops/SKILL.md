---
name: "navigate-clanker-ops"
description: "Navigate and understand the Clanker Ops extension system: dispatch pipeline, agent registry, plan generation, background spawning, command routing, state management, intercom handling, and board rendering."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Navigate Clanker Ops

Navigate the Clanker Ops extension system: dispatch pipeline, agent registry, plan generation, background spawning, command routing, state management, intercom handling, and board rendering.

## When to Use

- Debugging Clanker Ops dispatch failures (plan_exists, agent_not_found, auto_spawn errors)
- Adding a new `/clanker` subcommand or handler
- Understanding the dispatch lifecycle (plan → agent → config → spawn)
- Modifying the Clanker Ops state management or store
- Working with the board rendering system
- Implementing intercom event handling for subagent lifecycle

## Architecture Overview

```
commands/router.ts  ← entry point for /clanker commands
       │
       ▼
dispatch.ts  ← assembles dispatch payload (plan + agent + task)
       │
       ├── agent-registry.ts   ← discovers .pi/agents/*.md
       ├── plan-generator.ts   ← auto-generates plan files
       ├── config-builder.ts   ← builds runner config JSON
       └── process-spawner.ts  ← spawns background subagent
       │
       ▼
intercom/  ← event listener for subagent lifecycle
       ├── event-types.ts     ← event classification
       ├── plan-audit.ts      ← audit trail logging
       └── state-updater.ts   ← state mutations + artifact polling
       │
       ▼
state/  ← persistent state management
       ├── store.ts              ← file-backed state I/O
       ├── state-reducer.ts      ← immutable task mutations
       ├── selectors.ts          ← filtered task queries
       ├── invariants.ts         ← state validation
       ├── task-factory.ts       ← task creation
       ├── update-mutator.ts     ← partial updates
       ├── transition-validator.ts ← status transitions
       └── i18n-bridge.ts        ← message templates
       │
       ▼
view/  ← board rendering
       ├── board.ts       ← ANSI board renderer
       ├── board-model.ts ← data-to-view mapping
       └── format.ts      ← text utilities
```

## Key Files and Their Roles

### Entry Point & Routing
- **`index.ts`** — Extension registration, tool registration, notify setup
- **`commands/router.ts`** — Routes `/clanker` subcommands (board, help, dispatch, eod, bulk, log, focus) to handlers
- **`todo.ts`** — Tool registration (`/clanker` command → `handleClanker` → `routeCommand`)
- **`todo-overlay.ts`** — Board overlay utilities

### Dispatch Pipeline (plan → agent → task → background spawn)
- **`agent-registry.ts`** — Scans `.pi/agents/*.md`, parses AgentDefinition (name, role, systemPrompt), caches, resolved by owner name
- **`dispatch/plan-generator.ts`** — Auto-generates `#N_plan.md` files from task description + agent role. Creates Intended Outcome, Step-by-Step, Verification, Dependencies, Audit sections
- **`dispatch.ts`** — `assembleDispatch(taskId)`: reads state → finds task → resolves agent → reads plan → extracts sections → builds subagent task instruction → returns DispatchPayload
- **`dispatch/config-builder.ts`** — Maps DispatchPayload to pi-subagents RunnerConfig JSON (steps, resultPath, controlConfig, intercomTargets)
- **`dispatch/process-spawner.ts`** — `spawnBackgroundProcess`: spawns detached child process with jiti runner. Falls back to command string if auto-spawn fails
- **`dispatch/resolver.ts`** — Resolves jiti CLI path and pi-subagents runner script path from node_modules

### State Management
- **`state/store.ts`** — `getState()` / `commitState()`: reads/writes state JSON to `.pi/todo-state.json`
- **`state/state-reducer.ts`** — `applyTaskMutation()`: immutable state transitions (create, update, bulk, delete, clear)
- **`state/task-factory.ts`** — Creates new task objects with defaults (id, status, metadata)
- **`state/transition-validator.ts`** — Validates status transitions (pending→in_progress→completed)
- **`state/update-mutator.ts`** — Partial state update logic
- **`state/selectors.ts`** — Filtered task queries for board views

### Intercom Lifecycle Events
- **`intercom/event-types.ts`** — ControlEvent classifier (event kind → metadata extraction)
- **`intercom/plan-audit.ts`** — Appends audit trail entries to plan files
- **`intercom/state-updater.ts`** — `handleIntercomEvent()`: classifies event → audits plan → updates task status → polls artifacts. Runs as periodic intercom listener

### Board Rendering
- **`view/board.ts`** — `renderClankerBoard()` (bordered) and `renderClankerBoardCompact()` (indentation-based). Uses ANSI box-drawing chars
- **`view/board-model.ts`** — Transforms raw tasks into display rows (groups by status, computes column widths)
- **`view/format.ts`** — Text formatting helpers (wrap, truncate, align)

## Procedure

### 1. Trace a dispatch lifecycle

When `/clanker dispatch #N to @agent` is called:

```
commands/router.ts handleDispatch()
  │
  ├── agent-registry.ts resolveAgent(owner)
  │     Scans .pi/agents/*.md → find match → cache
  │
  ├── dispatch/plan-generator.ts generatePlan()
  │     Writes .pi/todo-plans/#N_plan.md (if missing)
  │
  ├── dispatch.ts assembleDispatch(N)
  │     Reads plan file → extracts sections → builds task string
  │     Returns DispatchPayload { agent, task, planPath, runId, ... }
  │
  ├── state/state-reducer.ts applyTaskMutation("update")
  │     Updates task status → "in_progress", sets metadata (runId, dispatchedAt)
  │
  ├── dispatch/config-builder.ts buildRunnerConfig()
  │     Maps payload to pi-subagents RunnerConfig JSON
  │
  └── dispatch/process-spawner.ts executeBackgroundDispatch()
        Resolves jiti + runner paths → writes config JSON → spawns detached process
```

### 2. Add a new `/clanker` subcommand

1. **Open** `commands/router.ts`
2. **Add handler** function matching the `Handler` type signature: `type Handler = (ctx: CommandContext) => Promise<boolean>`
3. **Register** in the `handlers` record: `handlers["subcommand"] = handlerFunction`
4. **Update** `CLANKER_HELP` string to advertise it
5. For **interactive-only** commands, check `ctx.hasUI` and return `ERR_REQUIRES_INTERACTIVE` if false

### 3. Debug dispatch failures

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| `agent not found` | `.pi/agents/AGENT_NAME.md` missing or has wrong filename | Create the agent definition or use correct owner name |
| `plan file not found` | `.pi/todo-plans/#N_plan.md` missing | Run `/clanker dispatch #N to @agent` (auto-generates plan) or call `generatePlan()` |
| `jiti CLI not found` | Jiti not resolveable from node_modules | Check `resolver.ts` resolution order; install jiti or adjust paths |
| `runner script not found` | pi-subagents runner missing | Check pi-subagents installation; verify `subagent-runner.ts` path |
| Auto-spawn pid undefined | Spawn failed to produce PID | `spawnBackgroundProcess()` with unref: true — process may exit before PID assigned. Fall back to manual command |
| Config write failed | `/tmp/clanker-dispatch/` permissions | Check temp directory write access |

### 4. State management patterns

- **Read**: `getState()` from `store.ts` → always returns the current state from `state.tasks`
- **Write**: `applyTaskMutation(state, op, params)` → returns `{ state: newState, op: result }` → `commitState(result.state)` persists
- **Operations** (in `state-reducer.ts`):
  - `create` → adds new task via `task-factory.ts`
  - `update` → partial update via `update-mutator.ts`, validates transition via `transition-validator.ts`
  - `bulk` → batch updates matching ID list
  - `delete` → tombstone (sets status to "deleted")
  - `clear` → reset all tasks
- **Invariants**: `state/invariants.ts` validates state shape before commit

### 5. Intercom lifecycle event flow

When a dispatched subagent fires control events (needs_attention, active_long_running):

```
intercom-handler.ts handleIntercomEvent(event)
  │
  ├── event-types.ts classify(event)
  │     Returns { kind, taskId, agent, runId, ... }
  │
  ├── plan-audit.ts appendAuditEntry(planPath, entry)
  │     Appends timestamped row to plan file Audit table
  │
  └── state-updater.ts updateTaskStatus()
        Applies state mutation to update task status from subagent events
```

### 6. Board rendering

- **Bordered view** (`renderClankerBoard`): Uses `╭─╮╰─╯│` box chars. Groups tasks by status column. Handles overflow (title truncation, row wrapping)
- **Compact view** (`renderClankerBoardCompact`): Indentation-based, no borders. Each task is `  #N  title  [status]`
- **Board model** (`board-model.ts`): Transforms raw `Task[]` into `DisplayRow[]`. Controls: column widths, gap calculation, overflow handling
- **Key rendering guard**: Title row overflow calculation must account for summary column width:

```typescript
// In board-model.ts — the gap must be deducted from available width
const gap = (numCols - 1) * columnGap;
const titleWidth = availableWidth - otherColumnWidths - gap;
```

## Verification

- [ ] `commands/router.ts` routes all subcommands correctly (especially: dispatch, bulk, eod, log, help, focus)
- [ ] Plan file exists at `.pi/todo-plans/#N_plan.md` before dispatch
- [ ] Agent exists at `.pi/agents/NAME.md` before dispatch
- [ ] Auto-spawn produces either PID + "Auto-fired" message OR fallback command
- [ ] `getState()` returns consistent state between mutations
- [ ] Board renders without ANSI artifacts in both bordered and compact modes
- [ ] Intercom events update task status and append audit trail
- [ ] All paths are in `.pi/extensions/clanker-ops/`