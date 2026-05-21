---
name: large-task-decomposition-orchestration
description: "Decompose a large monolithic TODO into well-scoped, dispatchable subagent tasks in Clanker Ops: create plan files, assign proper agent types (worker/scout/researcher), handle scout findings back as new tasks, and dispatch in parallel."
version: 1
created: 2026-05-19
updated: 2026-05-19
---
# Large Task Decomposition and Subagent Dispatch Orchestration

## When to Use

Use this skill when faced with a large, monolithic TODO that needs to be broken into discrete, actionable work items for parallel subagent dispatch. This is the **preparatory orchestration** step before dispatching individual tasks.

**Trigger phrases**: "break apart this TODO", "create subagent tasks", "decompose into actionable items", "split into dispatchable tasks", "orchestrate the work", "create plan files for subagents"

**Context**: This project uses Clanker Ops for task tracking, with three agent types for dispatch: `@worker` (implementation), `@scout` (investigation/discovery), `@researcher` (codebase research). Scouts feed findings back as new tasks.

## Procedure

### Step 1: Read and understand the monolithic TODO

Start by reading the full TODO document or master plan to understand scope:

```bash
# Read the source TODO
cat <path-to-todo>
```

Identify:
- **Implementation tasks**: Code changes, schema migrations, new files
- **Discovery tasks**: Codebase audit, API inspection, existing pattern analysis
- **Research tasks**: Cross-file dependencies, architectural understanding

### Step 2: Break into discrete, well-scoped work items

Each work item should be:
- **Independent**: Can be worked on without waiting for another task (avoid sequential dependencies)
- **Completable in one session**: ~15-30 minutes of real work
- **Single-responsibility**: One clear outcome per task
- **Testable**: Has a clear verification step

**Example decomposition** (from GRAPH_TODO):

| Task | Scope | Agent Type |
|------|-------|-----------|
| Add event_group_id column to health_metrics | Schema + migration | @worker |
| Group multi-metric ingestion events | Ingestion logic | @worker |
| Add same-event graph linking | Service + dedup | @worker |
| Wire exercise impact to graph edges | Pattern service | @worker |
| Wire overnight hypo to graph edges | Pattern service | @worker |
| Add provenance_json to health_metric_edges | Schema + migration | @worker |
| Create shared scoring utility | Utility module | @worker |
| Add GET event-group API endpoint | API route | @scout first → @worker |
| Migrate graph endpoints to require_active_user auth | Auth migration | @scout first → @worker |
| Photo ingest CGM reading from Dexcom | New feature | @worker |
| Wire insulin correlation to graph edges | Pattern service | @worker |
| Add graph edges RAG context | RAG integration | @worker |
| Add comprehensive graph edge tests | Tests | @worker |

### Step 3: Create Clanker Ops tasks

For each work item, create a Clanker Ops entry with:

```bash
# Create task with descriptive title, tags, and detailed description
todo({ action: "create", subject: "...", labels: ["graph", "backend", "p0"], description: "..." })
```

**Description format** — must be concrete enough that any agent knows what to do:

```
✅ Good: "Add nullable UUID event_group_id column to health_metrics table. Add index (user_id, event_group_id). Backfill existing rows as null. Update HealthMetricCreate and HealthMetricResponse schemas. Update HealthMetricService.create() and create_batch()."

❌ Bad: "Add event grouping support"
```

### Step 4: Create plan files

Write a `.pi/todo-plans/#N_plan.md` file for each task with the standard Clanker Ops plan structure:

```markdown
# Clanker Ops #N: [Task Title]

Status: pending
Owner: @unassigned
Tags: #p0 #backend #graph
Branch: dad_1805

## Intended Outcome
One-paragraph description of what the task will achieve.

## Step-by-Step
1. Step one...
2. Step two...
3. Step three...

## Verification
- [ ] Criterion 1
- [ ] Criterion 2

## Dependencies
- None (or reference other task IDs)

## Audit (EOD Report-Back)
- Tokens used: ~X
- Status: pending
```

### Step 5: Assign agent types

Based on task nature, choose the right agent:

| Agent | Role | When to Assign | Tools |
|-------|------|---------------|-------|
| **@scout** | Investigation / discovery | Task needs codebase audit: "Find all routes using user_id as Query param", "Check if method exists in model", "List all files touching X" | bash, find, ls, grep, read |
| **@researcher** | Cross-file research | Task needs architectural understanding: "Map the data flow from API to DB", "Find circular import risks" | bash, find, ls, grep, read |
| **@worker** | Implementation | Task produces code changes, file edits, tests, migrations | bash, todo, git, write, edit |

**Scout-then-worker pattern**: When the task involves uncertainty (e.g., "migrate auth on all graph endpoints"), dispatch a scout FIRST to discover the scope, then create a follow-up task for the @worker with concrete findings baked into the description.

```bash
# Example scout findings → new worker task
# Scout returns: "Found 13 routes in app/api/metrics.py using user_id: int = Query(...)"
# Convert to worker task: "Replace user_id: int = Query(...) with user=Depends(require_active_user) on all 13 routes in app/api/metrics.py. Use user.id instead."
```

### Step 6: Dispatch in parallel

For independent tasks, set all to `in_progress` and update plan files with owner, then dispatch:

```bash
# 1. Update task status and assignment in the state
todo({ action: "update", id: N, status: "in_progress", assignee: "@worker" })

# 2. Update plan file to show owner
# Append "Owner: @worker" to the plan file

# 3. Use send/dispatch to hand off
todo({ action: "send", id: N, assignee: "@worker" })
```

**Parallel dispatch strategy**: Set all non-conflicting tasks to `in_progress` before dispatching any. This tells the board they're all active. Then dispatch each in turn.

### Step 7: Handle scout findings

Scout findings often reveal new work items or change existing plans. When a scout returns:

1. Read the scout output carefully
2. Create new Clanker Ops tasks for each actionable finding
3. Tag the new tasks appropriately (#p0, #p1) based on severity
4. Reference the scout task that produced the findings

**Example** (from commit ec6a2b5 / task #3):
```
SCOUT FINDINGS: event_group_id EXISTS in models/ingestion.
get_event_group() method EXISTS.
MISSING: event-group endpoint (→ create #31).
MISSING: auth migration on 13 routes (→ create #32).
```

### Step 8: Follow up after dispatch

After all dispatched tasks complete:

1. **Verify completion**: Check each task's output or git diff
2. **Reconcile scouts**: Any pending findings that need addressing?
3. **Run tests**: Full test suite to catch regressions
4. **Update plan files**: Mark completed tasks with status and token audit
5. **Commit**: Ensure all work is committed with descriptive messages

```bash
# Full regression
python -m pytest tests/ -x --timeout=120
```

## Pitfalls

### Task scope creep
A single task that says "Wire exercise + sleep + insulin detections" became 3-4 commits. Decompose more aggressively — each detection method should be its own task if they touch different code paths.

### Scout findings create unplanned work
Expect scouts to find 2-3x more work than originally scoped. Budget for this by keeping scout tasks lightweight and fast (read-only, no implementation). Create follow-up worker tasks from findings.

### Parallel dispatch requires non-conflicting tasks
Tasks that touch the same files should be dispatched sequentially, not in parallel. Check path overlap:
- `app/services/pattern_service.py` changes → only one @worker at a time
- `app/api/metrics.py` changes → only one @worker at a time
- Independent files (`app/metrics/types.py` vs `tests/` vs `docs/`) → safe to parallelize

### Plan file orphan detection
When tasks are deleted or consolidated, check for orphaned `.pi/todo-plans/#N_plan.md` files:
```bash
ls .pi/todo-plans/ | grep -v -F -f <(grep -o '"id": [0-9]*' .pi/todo-state.json | awk '{print "#"$2"_plan.md"}')
```

### Scout cannot implement
If you dispatch a scout and expect it to also make changes, it won't. Scouts are read-only. Always create a separate @worker task for implementation, with the scout's findings baked directly into the description.

### Async dispatch for workers is unreliable
`subagent({ async: true })` for worker tasks has been shown to produce planning text instead of actual tool calls. Prefer:
- Scouts via subagent (read-only, reliable)
- Workers via direct execution in parent session
- Or use `todo({ action: "send", assignee: "@worker" })` handoff for synchronous dispatch

## Verification

- [ ] Each new task has a concrete, actionable description — no vague TODOs
- [ ] Each task has a plan file (`#N_plan.md`) with all required sections
- [ ] Tasks are tagged with priority (#p0, #p1) and category (#backend, #graph, #api)
- [ ] Worker tasks have no "investigate" or "find" language — those belong on scouts
- [ ] Scout findings are converted to new tasks (or noted as out-of-scope)
- [ ] No conflicting file paths between parallel-dispatched tasks
- [ ] Full test suite passes after all dispatched tasks complete
- [ ] Git log reflects the full chain of work with descriptive commit messages