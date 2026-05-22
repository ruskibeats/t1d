# Clanker Ops Extension — Comprehensive Technical Review

**Date:** 2026-05-20  
**Reviewer:** TypeScript / Systems Review  
**Scope:** `.pi/extensions/clanker-ops/`, supporting agents, prompts, and CLI tooling  
**Objective:** Determine whether the implemented system aligns with the documented intent that "the clanker board dispatches agents (clankers) that follow the attached plan and execute."

---

## 1. Executive Summary

**Verdict:** The Clanker Ops extension is a **sophisticated task-management UI and state reducer** built on top of a **non-existent agent orchestration engine**. The fundamental promise — that the board can dispatch agents to execute plans — is **entirely unimplemented**. The gap between the documented architecture and the running code is not a missing feature but a **missing architectural layer**.

What exists today is a manual orchestration surface: a human (or an attentive LLM acting as Controller) must read the board, read the plan file, manually invoke `pi-subagent` with the correct agent and task, and then manually update the board when done. This is not what the system documentation (`AGENTS.md`, `IDENTITY.md`, operator prompts) describes.

---

## 2. What the Extension Actually Does

### 2.1 Extension Core (`clanker-ops/`)

| Component | Actual Function |
|-----------|---------------|
| `index.ts` | Registers the `todo` tool and `/clanker` command. Rebuilds state from branch replay on session lifecycle events. |
| `todo.ts` | Tool/command registration shell. Implements the `todo` tool (CRUD for tasks) and `/clanker` command (board display + add interception). |
| `state/state-reducer.ts` | Pure reducer for task mutations (`create`, `update`, `list`, `get`, `delete`, `clear`). Includes cycle detection in `blockedBy` graphs. |
| `state/store.ts` | Module-level live state cell (`state: TaskState`). |
| `state/replay.ts` | Reconstructs state from Pi branch history by scanning `toolResult` entries where `toolName === "todo"`. |
| `view/board.ts` | ANSI-art board renderer. Reads `.pi/todo-state.json` directly for display. |
| `tool/response-envelope.ts` | Formats tool output for LLM consumption. |
| `tool/types.ts` | Core `Task` interface and TypeBox parameter schema. |

### 2.2 CLI Layer

| Tool | Location | Actual Function |
|------|----------|---------------|
| `clanker` | `/usr/local/bin/clanker` (bash + `jq`) | Direct JSON mutator on `.pi/todo-state.json`. Supports `list`, `add`, `move`, `status`, `change`. |
| `clanker-board` | `/usr/local/bin/clanker-board` (Node.js) | Imports `view/board.ts` and renders the ANSI board. Supports `--context-only` for external agents. |

### 2.3 Supporting Ecosystem

- **`.pi/agents/*.md`** — Rich agent definitions (role, context, conventions, verification steps). Currently **orphan documents** with no code path that reads them.
- **`.pi/prompts/clanker-ops/*.md`** — Excellent prompt guidance for planning, dispatch, closeout, and review. Currently **advisory text only** with no enforcement.
- **`.pi/todo-plans/#ID_plan.md`** — Plan files with `## Execution Protocol`, `## Steps`, `## Verification`. The board renderer detects their existence for display but the extension does not parse or act on them.

---

## 3. Detailed Gap Analysis

### Gap 1: No Dispatch Engine — CRITICAL

**The Problem:** There is zero code anywhere in the extension that knows how to invoke a Pi subagent. The `owner` field (e.g., `@worker`) is purely decorative. When a user says "dispatch #11 to @worker", nothing bridges the task to an agent.

**Evidence:**
- `registerClankerCommand` in `todo.ts` handles subcommands `help`, `eod`, `focus`. Unrecognized input falls through to `add`. **There is no `dispatch` subcommand.**
- The `clanker` CLI bash script has actions `list`, `add`, `move`, `status`, `change`. **No `dispatch` action.**
- The `todo` tool's `TaskAction` union is:
  ```typescript
  type TaskAction = "create" | "update" | "list" | "get" | "delete" | "clear";
  ```
  No `dispatch` action exists.
- The `Task` interface has `owner?: string` — a free-text label, not a routing key:
  ```typescript
  interface Task {
    id: number;
    subject: string;
    description?: string;
    status: TaskStatus;
    blockedBy?: number[];
    owner?: string;        // Just a string!
    metadata?: Record<string, unknown>;
    createdAt: string;
    updatedAt: string;
  }
  ```

**Impact:** The entire concept of "Clankers" as executable agents is theatrical. The system can *label* a task with `@worker`, but it cannot *send* it to a worker.

---

### Gap 2: No Plan File Integration — CRITICAL

**The Problem:** The extension's `Task` data model is minimal and does not include plan linkage. The board renderer (`view/board.ts`) separately reads `.pi/todo-plans/#ID_plan.md` from disk for display, but the extension core cannot create, validate, or act on plan files.

**Evidence:**
- The `todo` tool creates tasks with only `id`, `subject`, `status`, `createdAt`, `updatedAt`. It cannot set `planFile`, `tags`, `assigned`, or `branch`.
- The `clanker` CLI bash script writes to `.pi/todo-state.json` which uses a **richer schema** (`planFile`, `assigned`, `tags`, `branch`), but the Pi extension does not know about these fields.
- `view/board.ts` function `planRef(item)` does this:
  ```javascript
  const planPath = join(process.cwd(), ".pi", "todo-plans", `#${item.id}_plan.md`);
  if (!item.description?.trim() && item.planHandoff?.status === "sent") return "planning";
  return item.description?.trim() || existsSync(planPath) ? `#${item.id}_plan.md` : "no";
  ```
  This is **display-only detection**. The reducer never validates plan existence before `in_progress` transition.

**Impact:** A task can be `in_progress` in the Pi tool state while its plan file is untouched, or vice versa. The plan file is invisible to the agent orchestration logic.

---

### Gap 3: No Owner-to-Agent Resolution — CRITICAL

**The Problem:** The `.pi/agents/` directory contains rich agent definitions with role context, project conventions, verification steps, and audit requirements. The extension has zero code that reads these files, maps an `owner` to an agent definition, or injects agent context into a subagent invocation.

**Evidence:**
- `tool/types.ts`: `owner?: string` — no enum, no validation, no registry lookup.
- `state-reducer.ts`: No owner validation during `create` or `update`.
- `view/board.ts`: Renders `owner` with color coding (`ansi.dad`, `ansi.tom`) but treats it purely as display data.
- `index.ts`: No file system watcher or agent registry initialization.
- `.pi/agents/worker.md` specifies:
  - Backend stack (FastAPI, SQLAlchemy 2.0, Pydantic v2)
  - Frontend stack (React/TS, Vite, Tailwind)
  - Domain package pattern
  - Dual-write pattern
  - Verification commands (`pytest`, import checks)
  - **But nothing in the extension reads this file when `@worker` is assigned.**

**Impact:** The system cannot determine *what* a `@worker` is supposed to do or *how* to invoke it. The agent definitions are orphan documents.

---

### Gap 4: No Execution Protocol Enforcement — HIGH

**The Problem:** The prompt files describe a rigorous execution protocol (e.g., `build-plan.md`):

```markdown
## Execution Protocol
- Register this task on Clanker Ops as `in_progress` before starting substantial work.
- Read this plan, update the `### Current Task State` block...
- Run the verification checks listed below.
- Before closing: update the `### Current Task State` block, run verification...
```

This is **just text in a markdown file**. There is no state machine, gate, or automated enforcement.

**Evidence:**
- `state-reducer.ts` `isTransitionValid` only checks status transition legality (`pending → in_progress → completed → deleted`). No protocol step validation.
- The `clanker` CLI `status` action blindly sets the status string:
  ```bash
  jq --arg id "$2" --arg status "$3" \
    '.items |= map(if .id == ($id|tonumber) then .status = $status | .updatedAt = "'$(timestamp)'" else . end)'
  ```
  No plan existence check. No verification gate. No closeout template requirement.
- The `Task` interface has no `verification`, `closeout`, or `protocolStep` fields.

**Impact:** The system trusts the LLM or human to follow protocol. A task can be marked `completed` with no plan, no verification, and no execution.

---

### Gap 5: Two Competing State Stores — HIGH

**The Problem:** There are **two separate state stores** with overlapping but divergent schemas, and they are not synchronized.

| Store | Written By | Schema | Location |
|-------|-----------|--------|----------|
| **Branch Replay State** | Pi `todo` tool | `TaskState` (`tasks[]`, `nextId`) | Embedded in Pi branch history |
| **JSON State File** | `clanker` bash CLI | Rich `items[]` with `planFile`, `tags`, `assigned`, `branch` | `.pi/todo-state.json` |

**Evidence:**
- `registerTodoTool` in `todo.ts` calls `commitState(result.state)` which writes to the module-level cell. The Pi system persists this via branch replay (`replay.ts` scans for `toolName === "todo"`).
- The `clanker` bash script uses `jq` to mutate `.pi/todo-state.json` directly, bypassing the Pi tool system entirely.
- `view/board.ts` reads `.pi/todo-state.json` directly, not the extension's state cell.
- `index.ts` lifecycle handlers (`session_start`, `session_compact`) replay from the Pi branch, not from the JSON file.

**Impact:** The Pi LLM sees one state. The human CLI sees another. They drift apart. A task created via `/clanker add` exists in the JSON file but may be invisible to the Pi tool. A task updated via the `todo` tool exists in the branch replay but may not be reflected in the JSON file that the board renderer reads.

---

### Gap 6: No Subagent Lifecycle Integration — CRITICAL

**The Problem:** The Pi system has a `subagent` tool (available to the LLM). The Clanker Ops documentation (`AGENTS.md`) explicitly references it:

```typescript
await subagent({
  "chain": [
    {"agent": "pattern_agent", "task": "Analyze glucose data"},
    {"agent": "conversation_agent", "task": "Explain {previous} to user"}
  ]
});
```

But the Clanker Ops extension has **no integration point** with the `subagent` tool.

**Evidence:**
- `index.ts` registers handlers for `session_start`, `session_compact`, `session_tree`, `session_shutdown`, `tool_execution_end`, `agent_start`.
- **No `subagent_start`, `subagent_end`, or `subagent_result` hooks exist.**
- There is no automatic task status update when a subagent begins or ends.
- There is no plan file auto-update with subagent results.
- The `dispatch.md` prompt says "dispatch the specified task to the requested owner" but provides no technical mechanism.

**Impact:** The Controller (human or LLM) must manually bridge the gap by reading the plan, translating it into `subagent` tool calls, and manually updating state. This is error-prone and contradicts the promised automation.

---

### Gap 7: The `todo` Tool Paradox — MEDIUM

**The Problem:** `IDENTITY.md` states: **"You MUST NOT use the Pi `todo` tool. It does not exist in this project's workflow."**

Yet the `clanker-ops` extension **registers itself as the `todo` tool**:

```typescript
export const TOOL_NAME = "todo";
// ...
pi.registerTool({ name: TOOL_NAME, ... });
```

And the Pi system **does** expose this tool to the LLM.

**Evidence:**
- `tool/types.ts`: `export const TOOL_NAME = "todo";`
- The `todo` tool is visible in the system prompt under available tools.
- In the review session itself, the Controller initially used the `todo` tool because it was available, before being corrected.

**Impact:** The system is self-contradictory. The extension presents as a `todo` tool while the project's governance documents forbid using it. This creates confusion about which interface is canonical.

---

### Gap 8: No Closeout Automation — MEDIUM

**The Problem:** The `closeout.md` prompt describes a structured closeout template with fields for status, summary, files changed, verification results, token/cost notes, residual risk, and follow-ups. But there is no place in the data model to store this, no auto-extraction from subagent results, and no enforcement before `completed` transition.

**Evidence:**
- The `Task` interface has no `closeout`, `audit`, `results`, or `followUps` fields.
- The `clanker` CLI has no `closeout` action.
- The board renderer does not display closeout status.
- `.pi/EOD_AUDIT.md` is mentioned as a destination for audit reports, but no code writes to it.

---

## 4. What Works Well

Despite the architectural gaps, the following components are genuinely well-engineered and should be preserved:

1. **ANSI Board Renderer** (`view/board.ts`):
   - Sophisticated visual layout with dynamic column sizing.
   - Color-coded priority (`p0` red, `p1` orange, `p2` green).
   - Owner highlighting (`@dad_웃` blue, `@tom_웃` green).
   - Plan reference detection (`#ID_plan.md` vs `no` vs `planning`).
   - Duplicate detection via normalized text comparison.
   - "Don't Forget" auto-sectioning based on tag heuristics.
   - "Top open work" and attention item generation for external agent context.

2. **State Reducer** (`state/state-reducer.ts`):
   - Pure, well-typed reducer with exhaustive `Op` union.
   - Cycle detection in `blockedBy` dependency graphs.
   - Illegal transition guards (`pending → in_progress → completed → deleted`).
   - Metadata merge with `null` key deletion support.

3. **Branch Replay** (`state/replay.ts`):
   - Correctly reconstructs state from Pi branch history.
   - Defensive `isTaskDetails` discriminator skips corrupt entries.
   - Enables session-to-session persistence without explicit save/load.

4. **Context Rendering** (`renderClankerContext`):
   - Generates structured markdown context for external agents (Cursor, Cline).
   - Includes operating rules, attention items (failed, blocked, missing plans, duplicates), and top work with plan snippets.

5. **Prompt Library** (`.pi/prompts/clanker-ops/`):
   - Well-structured guidance for `add-work`, `build-plan`, `dispatch`, `closeout`, `review-dupes`, `review-assigned-plan`, `lights-off-eod`.
   - Good separation of concerns and clear templates.

---

## 5. Recommendations

### 5.1 Immediate Fixes (Stop the Bleeding)

1. **Rename the Tool**  
   Change `TOOL_NAME` from `"todo"` to `"clanker"` or `"clanker_ops"`. This eliminates the paradox where the forbidden `todo` tool is actually the project's own extension.

2. **Unify State Stores**  
   Make the extension read from and write to `.pi/todo-state.json` instead of maintaining a separate branch-replay state. Or, conversely, make the `clanker` CLI use the Pi tool API. **Pick one source of truth.**

3. **Add `planFile` and `tags` to the Task Schema**  
   The extension's `Task` interface must match the JSON file's schema so that tasks created via either interface are mutually intelligible.

### 5.2 Short-Term (Enable Manual Dispatch)

4. **Add a `dispatch` Subcommand to `/clanker`**  
   ```
   /clanker dispatch #11 to @worker
   ```
   This should read `.pi/todo-plans/#11_plan.md`, load `.pi/agents/worker.md`, and construct a subagent task payload.

5. **Add `dispatch`, `plan`, and `closeout` to the `clanker` CLI**  
   ```
   clanker dispatch <id> to <owner>
   clanker plan <id>               # opens/edits plan file
   clanker closeout <id>           # prompts for closeout fields
   ```

### 5.3 Medium-Term (Enable Semi-Automation)

6. **Create a `clanker-dispatch` Module**  
   A Node.js module that:
   - Reads `todo-state.json` and plan files.
   - Maps owners to agent definitions (`.pi/agents/<owner>.md` with `@` stripping).
   - Invokes `pi.subagent` (or the Pi API equivalent) with constructed tasks.
   - Monitors subagent lifecycle via callbacks.
   - Updates task status automatically (`in_progress` on start, `completed` on success, `failed` on error).

7. **Add Agent Lifecycle Hooks to `index.ts`**  
   ```typescript
   pi.on("subagent_start", ...)   // → mark task in_progress
   pi.on("subagent_end", ...)     // → read result, update status/closeout
   ```

8. **Plan File Validation Gate**  
   Before allowing `in_progress` transition, verify:
   - Plan file exists (` .pi/todo-plans/#ID_plan.md`).
   - Plan has required sections (`## Execution Protocol`, `## Steps`, `## Verification`).
   - Owner is a known agent type (file exists in `.pi/agents/`).

### 5.4 Long-Term (The Vision)

9. **True Orchestration Engine**  
   A background capability that:
   - Polls the queue for ready tasks (`pending`, not blocked, has plan, has valid owner, within concurrency limits).
   - Dispatches them to available subagent slots.
   - Manages retries and failover.
   - Generates the EOD audit automatically from closeout data.

10. **Plan Compilation**  
    Automatically translate plan `## Steps` into subagent task `chain` or `parallel` mode using the Pi subagent API.

11. **Verification Automation**  
    After subagent completion, automatically run the `## Verification` checks (e.g., `pytest`, `npm test`, `docker build`) and gate the `completed` transition on pass.

---

## 6. Conclusion

The `clanker-ops` extension is a **beautiful task board** built on top of a **non-existent orchestration engine**. It has:

- ✅ Excellent ANSI visualization and color-coded priority semantics  
- ✅ Solid pure reducer with cycle detection and transition guards  
- ✅ Correct branch-replay persistence model  
- ✅ Rich prompt guidance for planning, dispatch, and closeout  
- ❌ **No dispatch mechanism** — `owner` is a label, not a routing key  
- ❌ **No plan file integration** — plans are display-only text files  
- ❌ **No agent resolution** — `.pi/agents/*.md` are orphan documents  
- ❌ **No execution protocol enforcement** — trust-based, no guardrails  
- ❌ **No subagent lifecycle integration** — manual bridge required  
- ❌ **Two unsynchronized state stores** — Pi branch vs JSON file drift  

The system is currently a **manual orchestration surface** where the Controller must act as the human glue between the queue, the plans, the agents, and the subagent tool. The missing layer is the **Orchestration Engine** that connects these well-built pieces into an autonomous system.

---

## 7. Current Implementation Status (2026-05-20)

**UPDATE:** The "CRITICAL" gaps identified above have been **successfully implemented**:

| Gap | Status | Implementation |
|-----|--------|----------------|
| No dispatch mechanism | ✅ **FIXED** | `dispatch.ts`, `background-spawner.ts` |
| No plan file integration | ✅ **FIXED** | Plan files loaded and parsed for dispatch |
| No agent resolution | ✅ **FIXED** | `agent-registry.ts` maps `@owner` to definitions |
| No subagent lifecycle integration | ✅ **FIXED** | `intercom-handler.ts` + wired in `index.ts` |
| Two unsynchronized state stores | ✅ **FIXED** | Unified on `.pi/todo-state.json` |

**Verified:** Task #12 was dispatched via `/clanker dispatch #12`, ran 65+ minutes, and completed. See `CLANKER_OPS_UPDATE.md` for details.

---

## 8. State File Schema Reference (`.pi/todo-state.json`)

Single canonical schema. Extensions read/write directly to this file.

```json
{
  "items": [
    {
      "id": 124,
      "item": "[BUTLER] Plan audit — verify all plan files...",
      "description": "# Intended Outcome...",
      "status": "pending",
      "assigned": "@dad_웃",
      "tags": ["remember", "butler"],
      "blockedBy": [120],
      "handoff": { "status": "sent", "sentAt": "2026-05-20T12:45:00Z" },
      "metadata": { "pid": 196464, "dispatchRunId": "abc123" },
      "planFile": "#124_plan.md",
      "branch": "main",
      "project": "t1d",
      "createdAt": "2026-05-20T10:00:00Z",
      "updatedAt": "2026-05-20T12:45:00Z"
    }
  ]
}
```

**Required:** `id`, `item`, `status`, `createdAt`, `updatedAt` | **Optional:** `description`, `assigned`, `tags`, `blockedBy`, `metadata`, `planFile`, `branch`, `project`, `handoff`

---

*End of Review*
