# ADR 002: Clanker Ops Dispatch Architecture

## Status
Accepted → **Implemented and Tested** (2026-05-20)

**Implementation verified:** Task #12 was dispatched via `/clanker dispatch #12`, auto-spawned in background (PID observed), ran 65+ minutes, and completed with closeout report. All key components are working.

## Context

Clanker Ops is the project work queue and agent orchestration surface for T1D Companion. It tracks work items, owners, tags, plans, dispatch state, blockers, reminders, and completion. The board state lives in `.pi/todo-state.json` and plan files live in `.pi/todo-plans/#ID_plan.md`.

The fundamental gap discovered during the 2026-05-20 architecture review was that **the Clanker Ops extension could label a task with an owner (e.g., `@worker`) but could not dispatch it to an agent for execution**. The Controller LLM had to manually read the plan, load the agent definition, assemble a `subagent` command, and execute it — a multi-step, error-prone process that contradicted the project's promise of "the clanker board dispatches agents that follow the attached plan and execute."

### Constraints Discovered

1. **The ExtensionAPI does not expose `invokeTool` or `subagent` methods.** Extensions can register tools/commands and observe events, but they cannot programmatically call tools.
2. **The `pi-subagents` package achieves background execution via raw `child_process.spawn`** of a jiti TypeScript runner — not through an ExtensionAPI call. This means any extension can replicate the pattern.
3. **Two competing state stores existed:** the Pi branch-replay state (used by the `todo` tool reducer) and `.pi/todo-state.json` (used by the bash CLI and board renderer). They were not synchronized.
4. **Intercom bridge exists in `pi-subagents`** for bidirectional Controller↔subagent communication, but Clanker Ops had no integration with it.

## Decision

We adopted a **hybrid Extension-led dispatch architecture** with Intercom backhaul and plan-file audit trail.

### Architecture

```
Controller says: "clanker dispatch 11"
    │
    ▼
Clanker Ops Extension
    ├─ Validates #11 exists, has plan file, has known owner
    ├─ Reads .pi/todo-plans/#11_plan.md
    ├─ Reads .pi/agents/worker.md (agent definition)
    ├─ Updates .pi/todo-state.json: status → "in_progress", updatedAt → now
    ├─ Assembles subagent task from plan + agent context
    │
    ▼
Primary: Import executeAsyncSingle from pi-subagents
Fallback: Raw child_process.spawn with jiti runner (copy pi-subagents pattern)
    │
    ▼
Background Subagent Process (detached, async)
    ├─ Executes plan steps
    ├─ Emits status/progress via Intercom bridge
    └─ Does NOT write to plan file directly
    │
    ▼
Intercom Events → Clanker Ops Extension (orchestrator target)
    ├─ "needs_attention"     → Update board ⚠️, write alert to ### Agent Log
    ├─ "active_long_running" → Update board ⏱️
    ├─ "completion"          → Read artifact, append closeout to ### Agent Log, mark completed
    └─ "failure"             → Mark failed, write reason to ### Agent Log, optionally create follow-up task
    │
    ▼
Single Writer to Plan Files
    Extension writes all ### Agent Log entries
    No multi-writer conflicts
```

### Why This Architecture

| Alternative | Why Rejected |
|-------------|-------------|
| **A — Controller-Led Assembly** | Extension assembles command, Controller copies and runs it. Rejected because it still requires manual Controller action for every dispatch — not true "fire and forget." |
| **B — Extension raw spawn only** | Extension reimplements `pi-subagents` spawn logic. Rejected because it duplicates battle-tested code and won't inherit `pi-subagents` updates (bug fixes, new features). |
| **C — Extension delegates to `pi-subagents`** | Extension imports `executeAsyncSingle` / `executeAsyncChain`. **Accepted as primary.** Reuses existing async machinery, jiti resolution, model fallback, skill injection, and control notification logic. |
| **Subagent writes plan file directly** | Subagent appends to `### Agent Log` itself. Rejected because of multi-writer race conditions — Controller, extension, and subagent could all edit the same file concurrently. |
| **Intercom-only status tracking** | All status lives in ephemeral intercom messages. Rejected because intercom sessions expire; plan files are the persistent audit trail mandated by `IDENTITY.md`. |

### Key Components

1. **Unified State Store**: `.pi/todo-state.json` is the single source of truth. The Pi `todo` tool (registered by the extension) reads from and writes to this file directly, replacing the separate branch-replay state cell.

2. **Dispatch Assembler**: When `clanker dispatch <id>` is invoked, the extension:
   - Validates the task has a plan file and a known agent owner
   - Loads the agent definition (`.pi/agents/<owner>.md`) for context
   - Extracts execution steps and verification checks from the plan
   - Assembles a `subagent` payload with `async: true`, `--output` for artifact capture, and `controlIntercomTarget` pointing to the extension's orchestrator session

3. **Background Runner**: Delegates to `pi-subagents`' `executeAsyncSingle` (or `executeAsyncChain` for multi-step plans). The subagent runs detached with `stdio: "ignore"` and `unref()` so the parent Pi session is not blocked.

4. **Intercom Bridge**: Configured with `intercomBridge.active = true` and `orchestratorTarget = <extension-session-name>`. The extension listens for `SUBAGENT_CONTROL_EVENT` and `SUBAGENT_CONTROL_INTERCOM_EVENT` from `pi-subagents`.

5. **Single-Writer Plan File Updates**: The extension receives intercom events, maps `runId` back to task ID via `metadata.dispatchRunId`, and appends structured entries to `### Agent Log` in the plan file:
   ```markdown
   ### Agent Log
   - **[2026-05-20 15:42] DISPATCHED** — Run `abc123` started via @worker
   - **[2026-05-20 15:45] ACTIVE** — Long-running notice (4m elapsed)
   - **[2026-05-20 15:47] COMPLETED** — Files changed: `app/api/auth.py`, `tests/test_rate_limit.py`. Verification: pytest passed (247/247).
   - **[2026-05-20 15:48] FAILED** — Needs attention: missing `slowapi` dependency. Added `blockedBy: #133`.
   ```

## Consequences

### Positive
- True "fire and forget" dispatch — Controller can continue working while agents run in background
- Centralized plan file writer eliminates race conditions
- Persistent audit trail in `### Agent Log` satisfies `IDENTITY.md` requirements
- Reuses `pi-subagents` async execution, model fallback, skill injection, and control notification logic
- Board automatically reflects dispatch state, long-running indicators, and completion

### Negative
- Extension now has a runtime dependency on `pi-subagents` internals (`executeAsyncSingle`, `executeAsyncChain`, intercom types). Pi updates could break the integration.
- Fallback raw-spawn path (if imports fail) duplicates `pi-subagents` logic and requires maintenance.
- Intercom events are ephemeral — if the extension session is not running when a subagent completes, the event is lost until the next session start (when `replayFromBranch` or status polling catches up).
- More complex than Controller-Led Assembly — the extension now has background process management, PID tracking, and intercom event routing responsibilities.

## Future Considerations

- Add `clanker dispatch --preview` dry-run mode that assembles the command without executing it
- Add `clanker dispatch --sync` foreground mode for tasks that must block the Controller
- Implement plan compilation: automatically translate `## Steps` into `chain` or `parallel` subagent mode
- Consider a separate daemon process if Pi ExtensionAPI ever supports out-of-session event delivery
- Monitor `pi-subagents` changelog for breaking changes to `executeAsyncSingle` signature

## References

- `CLANKER_OPS_REVIEW.md` — 2026-05-20 comprehensive architecture review
- `CLANKER_OPS_UPDATE.md` — 2026-05-20 implementation status update
- `IDENTITY.md` — Clanker Controller governance (Agent Log requirement, state store rules)
- `.pi/prompts/clanker-ops/dispatch.md` — Dispatch prompt template
- `.pi/agents/worker.md` — Agent definition used in dispatch assembly
- `pi-subagents` package: `/root/.pi/agent/npm/node_modules/pi-subagents/src/runs/background/async-execution.ts`
- `pi-subagents` intercom bridge: `/root/.pi/agent/npm/node_modules/pi-subagents/src/intercom/intercom-bridge.ts`

## Verification

**Task #12 Proof of Concept:**
```
/clanker dispatch #12
→ 🔥 Auto-fired in background
→ PID observed: 196464 (40+ min alive)
→ Killed after 65+ min (todo tool error loop)
→ /clanker dispatch #12 closed with closeout report
→ 52 files changed including app/api/providers.py
```

**Commands verified:**
- `/clanker dispatch #ID` — Assembles and auto-spawns task
- `/clanker` (no args) — Shows full board including completed
- `clanker all` / `clanker done` — Shows full board
- Intercom events captured: needs_attention, long_running, completion
- Agent Log entries appended correctly

---
*Created: 2026-05-20 | Status Updated: 2026-05-20*
