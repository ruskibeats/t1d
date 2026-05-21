---
name: "clanker-ops-plan-gap-fill"
description: "Identify Clanker Ops tasks missing plan files and batch-create them with proper structure. Cross-references todo-state.json against .pi/todo-plans/ to find gaps, then writes complete plan files for each missing task. Use when tasks exist on the board but have no corresponding #N_plan.md, especially after bulk task creation or board imports."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Clanker Ops Plan Gap Fill

## When to Use

Use this skill when Clanker Ops tasks exist in `todo-state.json` but lack corresponding plan files in `.pi/todo-plans/`. This commonly happens after:

- Bulk task creation via `todo create` (which doesn't auto-generate full plans)
- Board imports or migrations
- Sprint planning sessions where tasks were queued faster than plans were written
- Butler audits that reveal plan gaps

**Trigger phrases**: "fill missing plans", "create plans for tasks", "tasks without plans", "plan gap", "batch create plans", "write plans for new tasks"

**NOT for**:
- Decomposing a large monolithic TODO into new tasks -> use `large-task-decomposition-orchestration`
- Handling orphaned tasks that should be deferred/archived -> use `orphaned-task-handler`
- Writing a single plan file -> use `clanker-ops-plan-write`
- Updating existing plan structure -> use `clanker-ops-plan-bulk-update`

## Procedure

### Step 1: List existing plan files

```bash
ls -la .pi/todo-plans/
```

Extract the task IDs that already have plans (e.g., `#141_plan.md` -> `141`).

### Step 2: List all tasks from the board

```bash
# Get compact task list with IDs and statuses
jq -r '.items[] | "\(.id) [\(.status)] \(.subject // .description[:60])"' .pi/todo-state.json
```

**Note**: The top-level key is `items`, not `tasks`. Using `.tasks` will return null and cause a jq iteration error.

### Step 3: Cross-reference to find gaps

Compare the task IDs from Step 2 against the plan file IDs from Step 1. Any task ID without a corresponding `#N_plan.md` is a gap.

**Filter by status** -- focus on tasks that need plans:
- `pending` -> needs a plan before dispatch
- `in_progress` -> urgently needs a plan (work may be blocked)
- `completed` -> may not need a plan (work already done)
- `deleted` -> skip (tombstoned tasks don't need plans)

### Step 4: Read a reference plan for format

Read an existing well-formed plan to use as a template:

```bash
cat .pi/todo-plans/#N_plan.md  # pick any completed or well-structured plan
```

Key sections required (per `clanker-ops-plan-write`):
- Header: task ID, title, status, owner, tags, branch
- **Intended Outcome**: what the task achieves
- **Step-by-Step**: ordered actionable steps
- **Verification**: concrete pass/fail criteria
- **Dependencies**: other task IDs or "None"
- **Audit (EOD Report-Back)**: tokens, status

### Step 5: Read task details for each gap

For each task missing a plan, read its full details:

```bash
# Get full task details including description
jq '.items[] | select(.id == N)' .pi/todo-state.json
```

Use the task's `subject`, `description`, `tags`, `labels`, and `assignee` fields to populate the plan.

### Step 6: Write plan files

For each gap task, create `.pi/todo-plans/#N_plan.md` using the standard structure:

```markdown
# Clanker Ops #N: [AGENT_TYPE] Task Title

Status: pending
Owner: @unassigned
Tags: #tag1 #tag2
Branch: (optional)

## Intended Outcome

[One paragraph: what this task achieves, what "done" looks like]

## Step-by-Step

1. [Concrete first step]
2. [Concrete second step]
3. [Concrete third step]

## Verification

- [ ] Criterion 1
- [ ] Criterion 2

## Dependencies

- None (or task IDs this blocks on)

## Audit (EOD Report-Back)

- Tokens used: ~X
- Status: pending
```

**Agent type prefix**: Use `[WORKER]`, `[SCOUT]`, or `[RESEARCHER]` in the title based on the task's nature:
- Implementation/code changes -> `[WORKER]`
- Investigation/discovery -> `[SCOUT]`
- Cross-file research -> `[RESEARCHER]`

### Step 7: Verify

```bash
# Confirm all gap tasks now have plans
ls .pi/todo-plans/ | wc -l
# Should match the count of non-deleted tasks
```

## Pitfalls

### jq key mismatch
`todo-state.json` uses `.items` as the top-level array key, NOT `.tasks`. Always use `.items[]` in jq queries. Using `.tasks[]` silently returns null and produces iteration errors.

### Don't overwrite existing plans
Always check that a plan file doesn't already exist before writing. Creating a plan with the wrong task ID (e.g., from a stale gap list) can overwrite a valid plan.

### Plan quality from descriptions
Task descriptions from `todo create` are often brief. Expand them into full plans -- the description is a starting point, not the final plan. Add concrete steps, verification criteria, and dependencies.

### Status-aware plan writing
- `in_progress` tasks need plans urgently -- the agent may be blocked without one
- `pending` tasks can wait but should be filled before dispatch
- `completed` tasks may not need plans retroactively unless audit requires it

### Batch size
If there are many gap tasks (10+), consider creating plans in batches of 3-5 to avoid context window bloat and ensure each plan gets proper attention.

## Verification

- [ ] Every non-deleted task in `todo-state.json` has a corresponding `.pi/todo-plans/#N_plan.md`
- [ ] Each plan has all required sections: Intended Outcome, Step-by-Step, Verification, Dependencies, Audit
- [ ] No plan files were overwritten or duplicated
- [ ] Plan count matches active task count (excluding deleted)