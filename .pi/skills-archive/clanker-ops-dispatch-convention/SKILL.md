---
name: "clanker-ops-dispatch-convention"
description: "Clanker Ops dispatch protocol: how /clanker dispatch #N assembles subagent commands from plan files and agent definitions. Use when dispatching tasks, building dispatch features, or debugging why clanker dispatch doesn't trigger agents."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

Any time you need to dispatch a Clanker Ops task to a subagent, implement dispatch functionality in the extension, or debug why `clanker dispatch` isn't working.

## Procedure

1. **Validate task state**: Task must exist in `.pi/todo-state.json`, have `status` set (not `""`), and have a plan file at `.pi/todo-plans/#N_plan.md`.
2. **Auto-update on dispatch**: Set `status = "in_progress"`, set `updatedAt` to now, and write `metadata.dispatchRunId` to the task.
3. **Resolve agent**: Map `task.assigned` (e.g., `@worker`) to `.pi/agents/worker.md` via `agent-registry.ts`.
4. **Load plan**: Read `.pi/todo-plans/#N_plan.md` into the dispatch payload context.
5. **Assemble output**: Generate a fully-formed `subagent` CLI command string:
   ```
   subagent single --agent <agentName> --async true --output <dispatch-log-path> --task "Execute Clanker Ops task #N per the attached plan.\n\nPlan file: <planPath>\nAgent role: <role>\n\n<planContent>"
   ```
6. **Output to Controller**: The extension CANNOT directly invoke subagents (ExtensionAPI has no `invokeTool`/`subagent`). It outputs the assembled command for the human/Controller to execute.
7. **Background execution**: The `subagent` tool with `--async true` spawns via `child_process.spawn` (jiti runner), so the human session remains unblocked.
8. **Status tracking via Intercom + Plan File**: The extension listens to `subagent_control_intercom_event` events, maps `runId` back to task ID, and appends structured status to the `### Agent Log` section of the plan file. The extension is the single writer to plan files.

## Pitfalls

- **Do NOT** try to call `subagent` programmatically from inside the extension — ExtensionAPI doesn't expose it. Output the command text instead.
- **Do NOT** use Python runtime agent names like `coordinator` — valid Pi subagents are `@worker`, `@scout`, `@researcher`, `@reviewer`, `@planner` from `.pi/agents/*.md`.
- **Do NOT** leave task `status` as `""` (empty string) — it makes tasks invisible to board views and can break Gemini API enum validation. The TypeBox schema must NOT include `""` in the enum array.
- **Do NOT** use unquoted property names starting with `-` in TypeScript types (e.g., `-type?: string;`). Use `"-type"?: string;` instead.
- Always quote property names that start with `-` or contain special characters in TypeScript interfaces.

## Verification

- Run `/clanker dispatch #<id>` — should output: `Dispatched #N → @<agent>` with plan path, runId, and assembled command.
- Board should show `⇢ #N` with `dispatched` tag and grey/active color.
- Copy-pasting the assembled `subagent` command into Pi should successfully start an async background run.
- `subagent({ action: "status", runId: "..." })` should return the run state without blocking.