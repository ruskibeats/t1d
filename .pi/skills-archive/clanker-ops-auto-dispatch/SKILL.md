---
name: "clanker-ops-auto-dispatch"
description: "Implement automatic background subagent dispatch in a Clanker Ops Pi extension. Covers the full pipeline from `/clanker dispatch #N` command to auto-firing a detached worker subagent without human copy-paste."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

Use when building or modifying a Clanker Ops Pi extension that needs to dispatch tasks to subagents automatically. This applies when:
- You have `/clanker dispatch #N` command that currently outputs a command for manual execution
- User wants "one-click" dispatch with background subagent firing
- Extension needs to bridge plan files (`.pi/todo-plans/#N_plan.md`) and agent definitions (`.pi/agents/*.md`) into live subagent runs

## Prerequisites

- Pi extension using `@earendil-works/pi-coding-agent` ExtensionAPI
- `pi-subagents` package installed (for dynamic import path)
- Agent definitions in `.pi/agents/<name>.md`
- Plan files in `.pi/todo-plans/#N_plan.md`
- `jiti` package resolvable (for fallback spawn path)

## Procedure

### Step 1: Assemble the Dispatch Payload

Create `dispatch.ts` that reads the agent definition and plan file:

```typescript
import { readFileSync } from "node:fs";
import type { Task } from "./tool/types.js";

export interface DispatchPayload {
  agent: string;           // agent name (e.g., "worker")
  role: string;            // role description from .md frontmatter
  task: string;            // assembled task instruction
  runId: string;           // unique run ID (e.g., crypto.randomUUID().slice(0, 13))
  planPath: string;
  outputPath: string;      // where subagent writes results
  subagentCommand: string; // human-readable command for manual fallback
}

export function assembleDispatch(
  task: Task,
  agentsDir = ".pi/agents"
): DispatchPayload {
  const agentFile = `${agentsDir}/${task.assigned?.replace("@", "")}.md`;
  const agentDef = readFileSync(agentFile, "utf-8");
  
  // Extract role from frontmatter or first heading
  const roleMatch = agentDef.match(/^#?\s*(.+)$/m);
  const role = roleMatch?.[1]?.trim() || "Implementation worker";
  
  const planPath = task.planFile || `.pi/todo-plans/#${task.id}_plan.md`;
  const runId = crypto.randomUUID().slice(0, 13);
  
  const taskText = `Execute Clanker Ops task #${task.id} per the attached plan.\n` +
    `Plan file: ${planPath}\n` +
    `Agent role: ${role}\n\n` +
    `Read the plan file, then implement all steps end-to-end.`;
  
  const outputPath = `.pi/todo-plans/dispatch-${task.id}-${runId}.md`;
  
  return {
    agent: task.assigned?.replace("@", "") || "worker",
    role,
    task: taskText,
    runId,
    planPath,
    outputPath,
    subagentCommand: `subagent single --agent ${task.assigned?.replace("@", "")} --async true --output ${outputPath} --task "${taskText}"`,
  };
}
```

### Step 2: Build the Auto-Spawner

Create `background-spawner.ts` with dual paths:

```typescript
import { spawn } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import type { DispatchPayload } from "./dispatch.js";

export async function autoSpawnSubagent(
  payload: DispatchPayload,
  ctx?: ExtensionContext
): Promise<{ success: boolean; runId?: string; error?: string }> {
  // PATH 1: Dynamic import of pi-subagents internals (preferred)
  try {
    const subagentsPath = require.resolve("pi-subagents");
    const { executeAsyncSingle } = await import(
      path.join(path.dirname(subagentsPath), "src/runs/background/async-execution.js")
    );
    
    const run = await executeAsyncSingle({
      agent: payload.agent,
      task: payload.task,
      output: payload.outputPath,
      async: true,
    });
    
    return { success: true, runId: run.runId };
  } catch (e) {
    // PATH 2: Fallback spawn with jiti
    return spawnFallback(payload);
  }
}

function spawnFallback(payload: DispatchPayload) {
  const jitiCliPath = require.resolve("jiti/cli.js");
  
  // Write config to temp file
  const tmpDir = "/tmp/pi-subagent-configs";
  fs.mkdirSync(tmpDir, { recursive: true });
  const cfgPath = path.join(tmpDir, `dispatch-${payload.runId}.json`);
  
  fs.writeFileSync(cfgPath, JSON.stringify({
    agent: payload.agent,
    task: payload.task,
    output: payload.outputPath,
    async: true,
  }, null, 2));
  
  // Resolve runner script from pi-subagents
  let runnerPath: string;
  try {
    const subagentsPath = require.resolve("pi-subagents");
    runnerPath = path.join(path.dirname(subagentsPath), "src/runs/background/subagent-runner.js");
  } catch {
    runnerPath = path.join(process.cwd(), "node_modules/pi-subagents/src/runs/background/subagent-runner.js");
  }
  
  const proc = spawn(process.execPath, [jitiCliPath, runnerPath, cfgPath], {
    cwd: process.cwd(),
    detached: true,
    stdio: "ignore",
    windowsHide: true,
  });
  
  proc.unref();
  
  return { success: true, runId: payload.runId };
}
```

### Step 3: Wire into `/clanker dispatch` Command Handler

In `todo.ts` or `index.ts` where `/clanker` command is registered:

```typescript
} else if (subcommand === "dispatch") {
  const parts = input.split(" ");
  const taskId = parseInt(parts[1]?.replace("#", ""));
  const owner = parts.length > 3 && parts[2] === "to" ? parts[3] : undefined;

  if (!taskId || Number.isNaN(taskId)) {
    ctx.ui.notify("Usage: /clanker dispatch #<id> [to <owner>]", "error");
    return;
  }

  const { assembleDispatch } = await import("./dispatch.js");

  if (owner) {
    const assignResult = applyTaskMutation(getState(), "update", {
      id: taskId,
      status: "in_progress",
      assigned: owner,
    });
    commitState(assignResult.state);
  }

  const task = getState().tasks.find((t) => t.id === taskId);
  if (!task) {
    ctx.ui.notify(`Task #${taskId} not found`, "error");
    return;
  }

  const payload = assembleDispatch(task);

  // Auto-spawn
  const { autoSpawnSubagent } = await import("./background-spawner.js");
  const spawnResult = await autoSpawnSubagent(payload, ctx);

  if (spawnResult.success) {
    // Update task with dispatch metadata
    const dispatched = applyTaskMutation(getState(), "update", {
      id: taskId,
      status: "in_progress",
      metadata: {
        dispatchRunId: spawnResult.runId || payload.runId,
        dispatchedAt: new Date().toISOString(),
      },
    });
    commitState(dispatched.state);

    ctx.ui.notify(
      `### Dispatched #${taskId} → ${task.assigned}\n\n` +
      `**Plan:** ${payload.planPath}\n` +
      `**Run ID:** \`${spawnResult.runId || payload.runId}\`\n` +
      `**Output:** ${payload.outputPath}\n` +
      `**Status:** Background worker started`,
      "info"
    );
  } else {
    // Fallback: output assembled command for manual execution
    ctx.ui.notify(
      `### Assembled Dispatch for #${taskId}\n\n` +
      `Copy and paste this command:\n\n` +
      "\`\`\`bash\n" +
      payload.subagentCommand +
      "\n\`\`\`",
      "info"
    );
  }
}
```

### Step 4: Handle Intercom Events

Create `intercom-handler.ts` to receive subagent lifecycle events:

```typescript
import { commitState, getState } from "./state/store.js";
import { applyTaskMutation } from "./state/state-reducer.js";

export function handleIntercomEvent(event: any) {
  const { runId, type, payload } = event;
  
  // Map runId back to task via metadata
  const state = getState();
  const task = state.tasks.find(
    (t) => t.metadata?.dispatchRunId === runId
  );
  
  if (!task) return;
  
  const logEntry = `**[${new Date().toISOString()}] ${type.toUpperCase()}** — Run \`${runId}\` ${payload?.message || ""}`;
  
  // Update task metadata log
  const updated = applyTaskMutation(state, "update", {
    id: task.id,
    metadata: {
      ...task.metadata,
      lastIntercomType: type,
      lastIntercomAt: new Date().toISOString(),
      agentLog: [...(task.metadata?.agentLog || []), logEntry],
    },
  });
  commitState(updated.state);
}
```

Register in `index.ts`:

```typescript
pi.onEvent("subagent_control_intercom_event", (event) => {
  const { handleIntercomEvent } = await import("./intercom-handler.js");
  handleIntercomEvent(event);
});
```

### Step 5: Update State Schema

Ensure `Task` type includes `metadata` field:

```typescript
export interface Task {
  id: number;
  subject: string;
  item?: string;  // legacy alias
  status: TaskStatus;
  assigned?: string;
  planFile?: string;
  metadata?: {
    dispatchRunId?: string;
    dispatchedAt?: string;
    lastIntercomType?: string;
    lastIntercomAt?: string;
    agentLog?: string[];
  };
  // ... other fields
}
```

### Step 6: Configure Pi Subagents for Intercom

Ensure `.pi/subagent-config.json` (or equivalent) has:

```json
{
  "control": {
    "notifyChannels": ["event", "intercom"]
  }
}
```

## Pitfalls

1. **ExtensionAPI does NOT expose `subagent` or `invokeTool`**. You cannot call `pi.subagent()` — you must import `pi-subagents` internals or spawn a process.
2. **Dynamic imports of `pi-subagents` internals are unstable**. Internal paths like `src/runs/background/async-execution.js` may change with package updates. Always implement the fallback `spawnRunner` path.
3. **Top-level await breaks CJS output**. Do not use `await import()` at module level in files loaded by the extension bundle. Use `await import()` inside function handlers only.
4. **Empty string enums break Gemini**. Remove `""` from JSON Schema enums sent to LLMs. Keep it in TypeScript types only for data compatibility.
5. **Property names starting with `-` must be quoted**. Use `"-type"?: string` not `-type?: string` in TypeScript interfaces.
6. **jiti CLI path may vary**. Use `require.resolve("jiti/cli.js")` rather than hardcoding the path.
7. **`write` tool is full-file overwrite**. Never use `write` to append to plan files — use `bash -c 'echo "..." >> file'` instead.

## Verification

1. `/clanker dispatch #11` should output "Dispatched #11 → @worker" not a copy-paste block
2. `subagent({ action: "status", id: "<runId>" })` should show the run as `running`
3. Task #11 metadata should contain `dispatchRunId` and `dispatchedAt`
4. Intercom events should update the task's `agentLog`
5. Board should show `⇢ #11` with `dispatched` tag

## References

- `pi-subagents` async execution: `src/runs/background/async-execution.ts` (uses `child_process.spawn`)
- ExtensionAPI docs: `@earendil-works/pi-coding-agent` — only `registerTool`, `registerCommand`, event hooks
- Clanker Ops state: `.pi/todo-state.json`
- Agent definitions: `.pi/agents/*.md`
- Plan files: `.pi/todo-plans/#N_plan.md`