---
name: "clanker-ops-plan-generator"
description: "Auto-generate plan files from task descriptions and agent definitions during Clanker Ops dispatch. Covers: plan file path resolution, exists check, content template with Intended Outcome/Step-by-Step/Verification/Audit sections, agent registry lookup, guard clauses for empty tasks, and wiring into the dispatch workflow with planFile metadata updates. Use when a /clanker dispatch call should produce a stub plan when none exists yet."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

- You're building or extending Clanker Ops dispatch and need auto-generated plan files
- A `/clanker dispatch #N to @agent` call should produce a stub plan when none exists
- You want to generate structured plan files with Intended Outcome, Step-by-Step, Verification, and Audit sections
- The plan should be populated from the task description + agent role definition

Do NOT use for:
- Manual plan authoring or editing by hand
- Plans that require human review before dispatch (this creates stubs, not final plans)
- Non-Clanker Ops workflow systems (this depends on Clanker Ops path and agent registry conventions)

## Procedure

### 1. Define the plan file path

Create a utility function that resolves the plan file path from a task ID. Plans live in `.pi/todo-plans/` with a `#N_plan.md` naming convention:

```typescript
import { join } from "node:path";

export function planFilePath(taskId: number): string {
  return join(process.cwd(), ".pi", "todo-plans", `#${taskId}_plan.md`);
}

export function planExists(taskId: number): boolean {
  return existsSync(planFilePath(taskId));
}
```

### 2. Define input/output types

Use explicit result types so the caller can react to failures without try/catch:

```typescript
export interface GeneratePlanInput {
  task: { id: number; item: string; description?: string; blockedBy?: number[] };
  agentName: string;
}

export interface GeneratePlanResult {
  generated: boolean;
  path?: string;
  reason?: string;
}
```

### 3. Implement the generation function

The function follows a guard-clause pattern:

1. **Plan exists check** — if `planExists(task.id)`, return `{ generated: false, reason: "Plan file already exists" }`
2. **Task content check** — if no `task.item` and no `task.description`, return `{ generated: false, reason: "Task has no description or title to generate a plan from" }`
3. **Agent resolution** — resolve the agent from the registry by name. If not found, return `{ generated: false, reason: "Agent not found" }`
4. **Build content** — call your template builder
5. **Write file** — use `mkdirSync(dirname(path), { recursive: true })` then `writeFileSync(path, content, "utf-8")`
6. **Return** — `{ generated: true, path }`

### 4. Build the plan content template

The plan should follow a consistent structure. The template includes the agent's role description to give the dispatched agent actionable context:

```markdown
# {task.item}

Auto-generated plan for dispatch to @{agent.name}
Generated: {YYYY-MM-DD HH:MM}

## Intended Outcome

{task.description or fallback to "Completed and verified."}

## Step-by-Step

Using the {agent.role} role:
1. Explore the codebase and understand the current state
2. Implement changes per the task description
3. Test the implementation
4. Document any findings

## Verification

- [ ] The implementation satisfies the task description
- [ ] Tests pass
- [ ] Changes follow established code patterns
- [ ] Documentation is updated if needed

## Dependencies

{task.blockedBy list or "None"}

## Audit

| Time | Event |
|------|-------|
| {timestamp} | Plan auto-generated for dispatch to @{agent.name} |

---

### Agent Log
```

### 5. Wire into the dispatch workflow

During `/clanker dispatch`, after finding the task and resolving the agent, call the plan generator and update the task metadata:

```typescript
// In dispatch handler:
import { generatePlan } from "../dispatch/plan-generator.js";
import { applyTaskMutation } from "../state/state-reducer.js";

// Auto-generate plan if missing
const planResult = generatePlan({ task, agentName: resolvedAgent });
if (planResult.generated) {
  // Update task with planFile reference so the board shows the filename
  applyTaskMutation(state, "update", {
    id: taskId,
    planFile: `#${taskId}_plan.md`,
  });
}
```

### 6. Update board rendering to show actual filenames

Replace any enum-based plan classification (returning `"yes"`/`"no"`) with actual filename resolution:

```typescript
export function getPlanRef(task: Task): string {
  if (!task.id) return "no";
  // Completed tasks always reference their plan
  if (task.status === "completed") return `#${task.id}_plan.md`;
  // Tasks with a description or that were dispatched have a plan
  if (task.description?.trim() || task.planHandoff?.status === "sent") return `#${task.id}_plan.md`;
  return "no";
}
```

## Pitfalls

- **Race conditions**: Always check `planExists()` before writing to avoid overwriting existing plans. The dispatch handler should only auto-generate when no plan exists.
- **Missing agent definition**: If the agent name doesn't match any registry entry, you can't include a role description. Fall back gracefully with `return { generated: false, reason: 'Agent not found' }` rather than crashing.
- **Empty task descriptions**: Tasks created with just a title and no description can't produce meaningful plans. Guard with a content check rather than generating a boilerplate-only plan.
- **Directory creation**: Always use `{ recursive: true }` on `mkdirSync` — the `.pi/todo-plans/` directory may not exist on first dispatch call. Without this, the write will throw.
- **Error reporting**: Return structured `{ generated: false, reason }` rather than throwing exceptions. The dispatch handler needs to decide whether to proceed without a plan.
- **File encoding**: Always specify `"utf-8"` encoding in writeFileSync for cross-platform consistency.

## Verification

1. ✅ `planExists(N)` returns `true` immediately after `generatePlan()` succeeds
2. ✅ Plan file on disk contains all required sections: Intended Outcome, Step-by-Step, Verification, Dependencies, Audit
3. ✅ Plan file includes the agent name and role description from the registry
4. ✅ Plan file uses the task description as Intended Outcome
5. ✅ Second call to `generatePlan()` on same task returns `{ generated: false, reason: "Plan file already exists" }`
6. ✅ Calling with a task that has no `item` and no `description` returns `{ generated: false, reason }` without writing any file
7. ✅ Calling with an unknown agent name returns `{ generated: false, reason: "Agent not found" }` without writing any file
8. ✅ Board rendering shows actual plan filenames (e.g. `#10_plan.md`) instead of `"yes"`/`"no"`
9. ✅ Task metadata includes `planFile` field after successful generation and state update