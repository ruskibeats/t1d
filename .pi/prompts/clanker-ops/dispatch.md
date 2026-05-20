# Prompt: Dispatch Clanker Work

Use when the user asks to send, dispatch, assign, or hand off a Clanker Ops task.

## Instruction

Dispatch the specified task to the requested owner. Include enough context for the worker to execute without guessing. Do not mutate unrelated tasks.

## Dispatch Message Shape

```text
Clanker Ops task: #<id> <title>
Owner: <owner>
Plan: .pi/todo-plans/#<id>_plan.md
Branch/context: <branch or project context if known>

Expected output:
- <what the worker should deliver>

Execution protocol:
- Mark #<id> in progress before substantial work.
- Read the plan first.
- Keep edits focused.
- Preserve user changes.
- Run verification checks.
- Close out with summary, changed files, checks, token/cost notes if available, residual risk, and follow-ups.

Verification:
- <checks>

Blockers/dependencies:
- <known blockers or none>
```

## Rules

- Default owner for generic dispatch is `@clanker`.
- If planning only, use `@planner`.
- If the user specifies an owner, use that owner.
- If the task has no plan, build or request a plan before dispatching unless the user explicitly says to dispatch anyway.
- If the task is blocked, do not dispatch as executable work unless the user explicitly overrides.
