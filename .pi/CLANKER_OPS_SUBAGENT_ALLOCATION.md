# Clanker Ops → Subagent Allocation Manual

> **How to use Clanker Ops (task board) + pi-subagents (execution engine) together**
> for the T1D Companion project.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Board States → Subagent Actions](#2-board-states--subagent-actions)
3. [Agent Roles & When to Dispatch](#3-agent-roles--when-to-dispatch)
4. [Dispatch Workflow](#4-dispatch-workflow)
5. [Slash Commands Quick Reference](#5-slash-commands-quick-reference)
6. [Chain Workflows (Multi-Step)](#6-chain-workflows-multi-step)
7. [Parallel Workflows](#7-parallel-workflows)
8. [Model Routing](#8-model-routing)
9. [Safety & Boundaries](#9-safety--boundaries)
10. [Troubleshooting](#10-troubleshooting)
11. [Appendix: Builtin Agent Reference](#11-appendix-builtin-agent-reference)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                   PI PARENT SESSION                   │
│                                                        │
│   ┌─────────────────┐     ┌─────────────────────────┐ │
│   │   Clanker Ops    │     │     pi-subagents         │ │
│   │  (.pi/todo-state.json)  │  (subagent tool)         │ │
│   │                  │     │                          │ │
│   │  Pending tasks   │────→│  dispatch worker/scout   │ │
│   │  In-progress     │←────│  result, artifacts       │ │
│   │  Completed       │     │  verification            │ │
│   └─────────────────┘     └─────────────────────────┘ │
│                                                        │
│              ┌────────────────────────────┐            │
│              │  Clanker Ops remembers:     │            │
│              │  assigned = @worker →      │            │
│              │  dispatch uses worker agent│            │
│              └────────────────────────────┘            │
└──────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                  ▼                  ▼
   ┌──────────┐      ┌──────────┐      ┌──────────────┐
   │  Worker   │      │  Scout   │      │  Researcher  │
   │(implements)│      │(scouts)  │      │(researches)  │
   └──────────┘      └──────────┘      └──────────────┘
```

**Key principle:** Clanker Ops owns the _what_ (task inventory, priority, assignment). pi-subagents owns the _how_ (execution via child sessions). The parent session bridges them.

### Files Involved

| File | Purpose |
|------|---------|
| `.pi/todo-state.json` | Clanker Ops task board — canonical state |
| `.pi/todo-plans/#N_plan.md` | Detailed plan for todo #N |
| `.pi/settings.json` | Project-level subagent overrides |
| `.pi/agents/*.md` | Custom agent definitions (worker, scout, etc.) |
| `~/.pi/agent/settings.json` | User-level subagent overrides |
| `~/.pi/agent/extensions/subagent/config.json` | Subagent extension config |

---

## 2. Board States → Subagent Actions

```
 ┌──────────┐     ┌──────────────┐     ┌──────────────────┐     ┌───────────┐
 │ PENDING  │────→│ IN_PROGRESS  │────→│ FINDINGS_INJECTED │────→│ COMPLETED │
 │          │     │              │     │                  │     │           │
 │ unstarted│     │ subagent     │     │ gaps turned into │     │ verified  │
 │          │     │ dispatched   │     │ new Clanker Ops  │     │ done      │
 └──────────┘     └──────────────┘     │ items (#N → N+1) │     └───────────┘
                       │               └──────────────────┘
                       ▼
               if blocked or failed:
                   ┌──────────────┐
                   │  BLOCKED     │ (create blocker todo,
                   │              │  keep original in_progress)
                   └──────────────┘
```

**Rules:**
- **PENDING** + `assigned: @worker` → ready to dispatch via worker agent
- **PENDING** + `assigned: @scout` → ready to dispatch via scout agent
- **PENDING** + `assigned: @researcher` → ready to dispatch via researcher agent
- **IN_PROGRESS** + no active subagent → a stalled task; investigate
- **IN_PROGRESS** + active subagent run id → live work; monitor completion
- **FINDINGS_INJECTED** — gaps, bugs, or TODO items discovered by scout/researcher are turned into new Clanker Ops items BEFORE completing the parent
- **COMPLETED** after subagent returns + verification passes + findings injected as new tasks (if any)

---

## 3. Agent Roles & When to Dispatch

### 3.1 Builtin Agent Reference

This project uses the [pi-subagents](https://github.com/nicobailon/pi-subagents) extension's builtin agents, with project-level overrides in `.pi/agents/`.

| Agent | Assignee Tag | Type | Use When Task Involves |
|-------|-------------|------|----------------------|
| **worker** | `@worker`, `@builder` | 🤖 droid | Implementation: write code, run tests, create files |
| **scout** | `@scout` | 🤖 droid | Codebase recon: inspect files, find patterns, audit |
| **researcher** | `@researcher` | 🤖 droid | Research: web/docs search, compare approaches, write reports |
| **reviewer** | `@reviewer` | 🤖 droid | Code review: correctness, edge cases, test coverage |
| **planner** | `@planner` | 🤖 droid | Planning: decompose tasks, write todo plans |
| **oracle** | `@oracle` | 🤖 droid | Second opinion: challenge assumptions, catch drift |
| **clanker** | `@clanker` | 🤖 droid | Fallback: simple tasks, housekeeping, docs |
| **butler** | `@butler` | `_` droid | Board hygiene, dupe combing, plan audit, roster sync, EOD reporting |
| **human** | `@tom_웃`, `@dad_웃` | `웃` human | Human review, decisions, design critique, prioritization, iOS setup, App Store |

> **Glyph convention:** Droids use `@name`. Humans use `@name_웃` (U+C6C3, Hangul syllable "us", meaning *smile*).
> Human tasks also get a `🧑` tag for color-coding on the board.

The `웃` at a glance shows a human-assigned task vs an agent.

### 3.2 Dispatch Decision Tree

```
Is the task clearly defined with a plan file?
├── YES → Is it implementation? (write code, create files)
│   ├── YES → assign @worker, dispatch with full plan
│   └── NO → Is it research/audit? (inspect code, compare patterns)
│       ├── YES → assign @scout or @researcher, dispatch
│       └── NO → assign @planner, have it write a plan first
│
└── NO → Is it urgent?
    ├── YES → write plan manually, then dispatch to appropriate role
    └── NO → assign @planner to create a plan, revisit

CRITICAL: After scout/researcher returns findings, inject gaps as new Clanker Ops items
before marking the original complete. Every gap found → a new todo.
```

---

## 4. Dispatch Workflow

### 4.1 The Standard Dispatch

**Pre-flight check ⧉/⊘:** Before dispatching, check the task for a ⊘ glyph (blocked) or ⧉ glyph (duplicate). If ⊘, inspect `blockedBy` — clear it if the blocker is already complete. If ⧉, check for an existing duplicate task and merge before dispatching.

```python
# 1. Mark IN_PROGRESS
todo({"action": "update", "id": 5, "status": "in_progress"})

# 2. Read the plan file
# (read .pi/todo-plans/5_plan.md)

# 3. Create handoff record so the Last column updates
import datetime
handoff_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
todo({"action": "update", "id": 5,
      "handoff": {"target": "@worker", "sentAt": handoff_time, "status": "sent"}})

# 4. Dispatch the subagent
subagent({
    agent: "worker",           # or "scout", "researcher"
    task: "Clanker Ops #5: [FEATURE] Add exercise log page\n" +
          "Description: From plan file:\n" +
          "- Create useExerciseLog hook with demo fallback\n" +
          "- Add ExercisePage with stat cards + form + list\n" +
          "- Wire into router and nav\n" +
          "Tags: #p1 #frontend\n" +
          "Branch: feature/exercise-log\n\n" +
          "Work this todo to completion. Report what changed, verification results, and any blockers.",
    async: true,               # background execution
    context: "fork",           # branched session from parent
    cwd: "/root/t1d"           # project root
})

# 4. Monitor (optional, async sends notification)
# subagent({ action: "status", id: "<run-id>" })

# 4. Verify artifacts
# git status, check files, run tests

# 5. (SCOUT/RESEARCHER ONLY) Inject findings as new Clanker Ops items
# Every gap, bug, or TODO found by the subagent becomes a new todo:
# todo({"action": "create", "subject": "[PARENT-N] Gap description", ...})
# Block new items on the parent: blockedBy=[PARENT_ID]

# 6. Mark COMPLETED
todo({"action": "update", "id": 5, "status": "completed"})
```

### 4.2 Dispatch with Scout (Read-Only Recon)

**Important: Search the FULL repo for existing files, not just `docs/` or `plan/` — use `find`.**
**Check for ⧉ (duplicates) on the Clanker Ops board before creating new tasks from findings.**

```python
todo({"action": "update", "id": 30, "status": "in_progress"})

subagent({
    agent: "scout",
    task: "Clanker Ops #30: Scout event_group_id usage\n" +
          "Check:\n" +
          "1) event_group_id usage in ingestion flows\n" +
          "2) graph API endpoints with auth\n" +
          "3) existing event-group endpoint\n" +
          "Report findings to /root/t1d/context.md",
    async: true,
    context: "fork",
    cwd: "/root/t1d"
})

# Scout is read-only — reliable even async

# CRITICAL: After scout returns, examine findings and inject gaps as new tasks:
# For each gap found:
#   todo({"action": "create",
#         "subject": "[#30.1] Missing X — implement Y",
#         "description": "Scout finding: ...",
#         "labels": [...],
#         "assignee": "@worker",
#         "blockedBy": [30]})
#
# Only mark parent complete AFTER all gaps are captured as todos.
# This makes each gap independently dispatchable and traceable.
```

### 4.3 Dispatch with Researcher (Analysis + Documentation)

```python
todo({"action": "update", "id": 24, "status": "in_progress"})

subagent({
    agent: "researcher",
    task: "Clanker Ops #24: [PHOTO] Food resolution service design\n" +
          "Research:\n" +
          "- Design FoodResolutionService interface\n" +
          "- Normalize labels (lowercase, singular/plural, remove adjectives)\n" +
          "- Search priority hierarchy: user-confirmed → curated → standard → community → model\n" +
          "- Rank candidates by similarity, trust, relevance\n" +
          "Produce a design doc at docs/design/food-resolution.md",
    async: true,
    context: "fork",
    cwd: "/root/t1d"
})
```


## 4.5 The Critical Rule: Findings Must Become Clanker Ops Items

**Every subagent (scout, researcher, reviewer) that returns findings must have those findings injected back into Clanker Ops as new actionable items before the parent task is marked complete.**

```python
# After subagent returns findings, for each gap found:
todo({"action": "create",
      "subject": "[#30.1] Missing event-group endpoint",
      "description": "Scout finding from #30",
      "labels": ["graph", "api", "p1"],
      "assignee": "@worker",
      "blockedBy": [30]})
todo({"action": "update",
      "id": 30,
      "description": "SCOUT FINDINGS: FOUND: X. MISSING: Z (→ #31)."})
todo({"action": "update", "id": 30, "status": "completed"})
```

### Why This Matters

- Each gap becomes **independently dispatchable**
- **Traceability** via blockedBy from child to parent
- **No orphaned gaps** — findings don’t rot in markdown files

### Pattern Summary

| Parent Type | After Subagent Returns | Before Marking Complete |
|-------------|------------------------|------------------------|
| Scout task | Examine findings, identify gaps | Create N new todos, update parent description |
| Researcher task | Identify design decisions and gaps | Create N new todos, update parent description |
| Reviewer task | Identify bugs, test gaps, issues | Create N new todos, update parent description |
| Worker task | Verify implementation succeeded | Usually no findings needed |

### Quick Checklist

```text
☐ Subagent returned findings
☐ Each gap → new Clanker Ops todo
☐ Check entire repo for existing files (don't assume docs/ path)
☐ Check for ⧉ (duplicate task already on board) before creating
☐ Child todos use blockedBy: [PARENT_ID], then clear blockedBy before dispatch if parent is complete
☐ Parent description updated with child task IDs
☐ Parent marked complete only after ALL gaps captured
☐ Plan file includes ## Audit section for EOD report-back
☐ NEVER change task assignees — @researcher, @builder, @scout, @tom_웃 are all valid
```

### 4.6 Plan File Requirement: Audit Section

**Every plan file (`.pi/todo-plans/#N_plan.md`) MUST end with an `## Audit` section** so dispatched agents report back for EOD aggregation:

```markdown
## Audit

After completing this task, report:
1. Files created or modified (full paths)
2. Verification results (tests passed, imports OK)
3. Gaps or findings discovered (even if unexpected)
4. Decision made (model used, approach chosen, tradeoffs)
5. Estimated tokens used (input + output, from subagent meta if available)
```

This feeds directly into the EOD audit at `.pi/EOD_AUDIT.md`. If every task reports back in this standard format, the daily EOD summary (see #28_plan.md) can aggregate without re-scouting the same files.

### 4.4 Dispatch with Implementation Verification (Trust But Verify)

```python
# Step 1: Worker does the work
subagent({
    agent: "worker",
    task: "Clanker Ops #16: [GRAPH] Delayed high-fat meal detection edges\n..." ,
    async: true,
    context: "fork",
    cwd: "/root/t1d"
})

# After worker returns:
# Step 2: Scout verifies
subagent({
    agent: "scout",
    task: "Verify Clanker Ops #16 completion:\n" +
          "- Check graph_service.py for meal_to_delayed_spike edge type\n" +
          "- Verify pattern_service.py has delayed spike detection\n" +
          "- Report what was implemented",
    async: true,
    context: "fork",
    cwd: "/root/t1d"
})

# Step 3: Reviewer audits
subagent({
    agent: "reviewer",
    task: "Review Clanker Ops #16 implementation:\n" +
          "Focus on: edge type naming, evidence structure, test coverage",
    async: true,
    context: "fork",
    cwd: "/root/t1d"
})
```

---

## 5. Slash Commands Quick Reference

These work after installing `pi-subagents` and work from the parent session directly (not inside subagents).

| Goal | Command |
|------|---------|
| Dispatch a single agent | `/run worker "Implement the exercise log feature"` |
| Dispatch with specific model | `/run worker[model=openrouter/owl-alpha] "Scout the auth flow"` |
| Dispatch background | `/run worker "Do this work" --bg` |
| Dispatch forked context | `/run worker "Continue this thread" --fork` |
| Combine fork + background | `/run worker "Do this in background" --fork --bg` |
| Check active async runs | `/subagents-doctor` or ask "show async runs" |

### Per-Step Configuration Addons

Append `[key=value,...]` to override per-step:

```
/run scout[output=context.md]        ← Save results to file
/run worker[reads=plan.md+context.md] ← Pre-load files
/run scout[model=openrouter/owl-alpha]  ← Override model
/run worker[skills=critical-thinking]   ← Inject specific skill
/run scout[output=context.md,model=openrouter/owl-alpha]  ← Multiple overrides
```

---

## 6. Chain Workflows (Multi-Step)

A chain runs agents sequentially, where each step gets the previous step's output as context via `{previous}`.

### 6.1 The Standard Implement → Review Chain

```python
subagent({
    chain: [
        { agent: "worker", task: "Implement event grouping from {task}" },
        { agent: "reviewer", task: "Review {previous} for correctness and test coverage" },
    ],
    task: "Clanker Ops #14: Event grouping foundation - add event_group_id to health_metrics",
    context: "fork",
    cwd: "/root/t1d"
})
```

### 6.2 Scout → Planner → Worker → Reviewer (Full Pipeline)

```python
subagent({
    chain: [
        { agent: "scout", task: "Analyze current auth flow in {task}", output: "context.md" },
        { agent: "planner", task: "Create implementation plan from {previous}", output: "plan.md" },
        { agent: "worker", task: "Implement the plan from {previous}" },
        { agent: "reviewer", task: "Review implementation from {previous}" },
    ],
    task: "Clanker Ops #X: Add rate limiting (slowapi) to login endpoints",
    context: "fork",
    cwd: "/root/t1d"
})
```

### 6.3 Chain with Fan-Out (Parallel Implementation → Single Review)

```python
subagent({
    chain: [
        { agent: "scout", task: "Analyze codebase for {task}", output: "context.md" },
        {
            parallel: [
                { agent: "worker", task: "Implement Feature A from {previous}" },
                { agent: "worker", task: "Implement Feature B from {previous}" },
                { agent: "worker", task: "Implement Feature C from {previous}" },
            ],
            concurrency: 2,     # max parallel workers
            failFast: true,     # stop on first failure
            worktree: true      # isolated git worktrees
        },
        { agent: "reviewer", task: "Review all changes from {previous}" },
    ],
    task: "Clanker Ops #X: Implement 3 new domain packages",
    context: "fork",
    cwd: "/root/t1d"
})
```

### 6.4 Chain with Variable Interpolation

Chain templates support these variables:

| Variable | Description |
|----------|-------------|
| `{task}` | Original task from the first step |
| `{previous}` | Output from the prior step |
| `{chain_dir}` | Path to shared chain artifact directory |

### 6.5 Slash Command Chains

```bash
# Sequential chain
/chain scout "scan the codebase" -> planner "create an implementation plan" -> worker "implement it" --bg

# Chain with shared task
/chain scout planner -- analyze the auth system

# Chain with per-step config
/chain scout[output=context.md] "scan code" -> planner[reads=context.md] "analyze auth"

# Parallel chain
/parallel scout "scan frontend" -> reviewer "check security"

# Run a saved chain file
/run-chain scout-planner -- refactor authentication
```

### 6.6 Saved Chain Files

Create reusable chains as `.chain.md` files in `.pi/chains/`:

```md
---
name: implement-and-review
description: Implement then review a todo
---

## worker
tasks: read, bash, write, edit, grep
model: openrouter/owl-alpha

Implement the following: {task}

## reviewer
tasks: read, bash, grep
model: openrouter/owl-alpha

Review the implementation from {previous}. Check correctness, test coverage, and edge cases.
```

Run with: `/run-chain implement-and-review -- Clanker Ops #5 exercise log feature`

---

## 7. Parallel Workflows

### 7.1 Parallel Implementation (Multiple Workers)

```python
subagent({
    tasks: [
        { agent: "worker", task: "Implement auth module" },
        { agent: "worker", task: "Implement API endpoints" },
        { agent: "worker", task: "Write tests" },
    ],
    concurrency: 2,        # max concurrent (rate-limit aware)
    worktree: true,        # isolated git worktrees
    context: "fork",
    cwd: "/root/t1d"
})
```

### 7.2 Parallel Review (Multiple Reviewers, Different Angles)

```python
subagent({
    tasks: [
        { agent: "reviewer", task: "Review for correctness and edge cases" },
        { agent: "reviewer", task: "Review test coverage and assertions" },
        { agent: "reviewer", task: "Review unnecessary complexity and code style" },
    ],
    concurrency: 3,
    context: "fork",
    cwd: "/root/t1d"
})
```

### 7.3 Parallel Scout (Multi-Area Audit)

```python
subagent({
    tasks: [
        { agent: "scout", task: "Inspect graph_service.py for missing event-group methods", count: 3 },
    ],
    concurrency: 1,   # sequential per-task for clean output
    context: "fork",
    cwd: "/root/t1d"
})
```

### 7.4 Worktree Isolation for Parallel Edits

When multiple workers write to the same repo, use `worktree: true` to create isolated git worktrees:

```python
subagent({
    tasks: [
        { agent: "worker", task: "Implement auth module" },
        { agent: "worker", task: "Implement API module" },
    ],
    worktree: true,   # each gets its own git branch + checkout
    context: "fork",
    cwd: "/root/t1d"
})
```

Requirements:
- Clean git working tree
- `node_modules/` is symlinked into each worktree
- After completion, per-agent diff stats are captured and worktrees cleaned

---

## 8. Model Routing

### 8.1 Current Verified Model (T1D-specific)

Based on empirical testing across the T1D project (see `.pi/agents/MODEL-ROUTING.md`):

| Agent | Model | Status |
|-------|-------|--------|
| All roles | `openrouter/owl-alpha` | ✅ Best all-around free model |

**Simplified to a single model** — `owl-alpha` works reliably across worker, scout, and researcher roles. No fallback models needed. Always free on OpenRouter.

### 8.2 Override Model Per Dispatch

```python
subagent({
    agent: "worker",
    task: "...",
    model: "openrouter/owl-alpha",   # explicit override
    context: "fork",
    cwd: "/root/t1d"
})
```

Slash command: `/run worker[model=openrouter/owl-alpha] "task"`

### 8.3 Persistent Override in Settings

Set a model override for a specific agent role in `.pi/settings.json`:

```json
{
  "subagents": {
    "agentOverrides": {
      "worker": { "model": "openrouter/owl-alpha" },
      "reviewer": { "model": "openrouter/owl-alpha" },
      "scout": { "model": "openrouter/owl-alpha" }
    }
  }
}
```

### 8.4 Model Routing Rules (T1D-specific)

| Rule | Detail |
|------|--------|
| **Always async** | `async: true` for all dispatches |
| **Always fork** | `context: "fork"` for branched session isolation |
| **Always cwd** | `cwd: "/root/t1d"` — explicit project root |
| **Max concurrency** | 2-3 concurrent agents — rate limits are per-model |
| **No thinking suffix** | Use bare model names, no `:high` suffix |
| **If 400 error** | Try model name without `:free` suffix |
| **If 429 error** | Reduce concurrency, wait 10 seconds |
| **Track run IDs** | Ghost completions arrive 30-120s late |

### 8.5 Previously Tested Models (Deprecated)

| Model | Verdict |
|-------|---------|
| `openai/gpt-oss-120b:free` | Planning prose only, no tool execution |
| `openai/gpt-oss-20b:free` | Planning prose only, no tool execution |
| `nvidia/nemotron-nano-9b-v2:free` | Works but owl-alpha more reliable |
| `nvidia/nemotron-3-nano-30b-a3b:free` | Inconsistent tool execution |
| `qwen/qwen3-coder:free` | Inconsistent tool execution |
| `deepseek/deepseek-v4-flash:free` | Free tier discontinued |
| `poolside/laguna-xs.2:free` | Inconsistent tool execution |
| `poolside/laguna-m.1:free` | Planning output, no tool calls |
| `baidu/cobuddy:free` | Planning output, no tool calls |
| `inclusionai/ling-ai/ling-2.6-flash:free` | No longer free |

---

## 9. Safety & Boundaries

### 9.1 Subagent Recursion Guard

Subagents **cannot** spawn their own subagents by default. The depth limit is 2 levels (parent → subagent → sub-subagent), implemented via environment variables:

```bash
# Set before starting Pi
export PI_SUBAGENT_MAX_DEPTH=1   # block all nesting
export PI_SUBAGENT_MAX_DEPTH=3   # allow one more level
```

**Never** set `PI_SUBAGENT_DEPTH` manually — it is propagated internally.

### 9.2 Child Safety Boundaries

Child subagent sessions:
- Do **not** receive the `subagent` tool (no spawning grandchildren)
- Do **not** receive the bundled pi-subagents skill
- Receive explicit boundary instructions: "You are not the parent orchestrator"
- Forked context filtering strips parent-only orchestration artifacts

### 9.3 Clanker Ops Discipline

| Rule | Why |
|------|-----|
| One task `in_progress` at a time | Prevents conflicting dispatches |
| Verify before marking complete | Subagents may claim completion without writing files |
| Create blocker todos for failures as new todos | Keeps original task visible while unblocking |
| Never mark completed from final prose alone | Check `git status`, file artifacts, test output |
| Plan files survive todo deletion | `.pi/todo-plans/` files are not removed by `todo clear` |

### 9.4 Emergency Escalation

If a subagent is stuck or producing bad output:

```python
# Soft-interrupt
subagent({ action: "interrupt", id: "<run-id>" })
```

Send a follow-up through resume:

```python
subagent({ action: "resume", id: "<run-id>", message: "New instructions: ..." })
```

**Last resort:** interrupt the child process and relaunch with corrected instructions.

---

## 10. Troubleshooting

### 10.1 Subagent Returns Planning Prose, No File Changes

**Cause:** Model doesn't execute tools reliably (common with `:free` tier models).

**Fix:** Use `openrouter/owl-alpha` as verified in MODEL-ROUTING.md. If still failing, execute directly in parent session.

### 10.2 Async Subagent Appears Stalled

**Check:** Run `subagent({ action: "status" })` to list active async runs.

**Possible causes:**
- Rate limit (429) — reduce concurrency, wait
- Fork failure — parent session not persisted
- Model returned 400 — try without `:free` suffix

**Fix:** Interrupt and relaunch with simplified instructions.

### 10.3 "Subagent completed" but No Files Changed

**Common with:** Async forked subagents on implementation tasks.

**Known pattern:** Async subagents read but don't reliably write files.

**Fix:**
1. Check `git status` — verify before accepting completion
2. If no changes, execute directly in parent session
3. Use subagents for scouting/research (reliable), not implementation (unreliable async)

### 10.4 Intercom Not Working

```bash
/subagents-doctor
```

Or just ask: "Check whether subagents and intercom are set up correctly."

**Troubleshoot:**
- Is `pi-intercom` installed? `pi install npm:pi-intercom`
- Does the session have a targetable name?
- Is intercom bridge enabled in config?

### 10.5 Ghost Completions (Delayed Notifications)

Async completions can arrive 30-120 seconds late. Track run IDs explicitly and check status rather than waiting for notification.

### 10.6 Chain Step Failed

If `failFast: true` is set, the chain stops on first failure. Inspect the failed step's output, fix, and relaunch from that step onward.

### 10.7 Worktree Setup Failed

Ensure:
- Inside a git repo with clean working tree
- No task-level `cwd` overrides (or they match the shared cwd)
- `node_modules/` exists in the main repo

---

## 11. Appendix: Builtin Agent Reference

### 11.1 Agent Summary Table

| Agent | Purpose | Tool Access | Context Mode | Best For |
|-------|---------|-------------|--------------|----------|
| **scout** | Fast codebase recon | read, grep, find, ls, bash | Fresh | Scoping tasks before planning |
| **researcher** | Web/docs research with sources | read, bash, web tools | Fresh | Research briefs, audits |
| **planner** | Concrete implementation plans | read, bash, grep, find | Forked | Breaking down vague tasks |
| **worker** | Implementation work | read, write, edit, bash, grep | Forked | Writing code, running tests |
| **reviewer** | Code review | Code review, small fixes | read, bash, grep | Fresh | Assurance |
| **oracle** | Second opinion, challenge assumptions | read, bash | Forked | Hard bugs, risky decisions |
| **context-builder** | Setup pass before planning | read, bash, grep, find | Fresh | Gathering context for big changes |
| **delegate** | General-purpose child agent | All parent tools | Fresh | Chores fitting no other role |

### 11.2 Prompt Recipes by Scenario

| Scenario | Recipe |
|----------|--------|
| "I need to understand this code" | `scout` → recapped, ask clarification |
| "What does the research say?" | `researcher` → `scout` (local code check) |
| "Plan this feature" | `scout` analysis → `planner` decomposition |
| "Implement this approved plan" | `worker` → `reviewer` → fix any issues |
| "Review this branch" | Multiple `reviewer` runs (correctness, tests, complexity) |
| "Second opinion on a hard bug" | `oracle` diagnosis before editing |
| "Stuck on a decision" | `oracle` to challenge assumptions |

### 11.3 Slash Command Index

| Command | Effect |
|---------|--------|
| `/run <agent> "task"` | Dispatch single agent |
| `/run <agent> "task" --bg` | Background dispatch |
| `/run <agent> "task" --fork` | Forked context |
| `/chain a "t1" -> b "t2"` | Sequential chain |
| `/parallel a "t1" -> b "t2"` | Parallel dispatch |
| `/run-chain <name> -- <task>` | Saved workflow from .chain.md |
| `/subagents-doctor` | Diagnostics |

### 11.4 Builtin Agent Frontmatter Reference

```yaml
---
name: worker
package:               # optional namespace
description: Autonomous implementation worker
tools: read, bash, write, edit, grep, ls, find
systemPromptMode: replace
inheritProjectContext: true   # respects AGENTS.md
inheritSkills: false
defaultContext: fork          # forked session by default
model: openrouter/owl-alpha
fallbackModels: []
maxSubagentDepth: 1
---
```

Key fields:

| Field | Description |
|-------|-------------|
| `tools` | Builtin tool allowlist. Omitted = all normal tools. `mcp:` for direct MCP tools. |
| `systemPromptMode` | `replace` (clean prompt) or `append` (keep base prompt) |
| `inheritProjectContext` | Whether child sees AGENTS.md / CLAUDE.md |
| `inheritSkills` | Whether child sees Pi's skills catalog |
| `defaultContext` | `fork` uses branched session; `fresh` uses clean child |
| `maxSubagentDepth` | Tighten nesting limit for this agent's children |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│              CLANKER OPS → SUBAGENT ALLOCATION                       │
│                    Quick Reference Card                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TODO @worker  → subagent(agent:"worker", async, fork)              │
│  TODO @scout   → subagent(agent:"scout",  async, fork)              │
│  TODO @researcher → subagent(agent:"researcher", async, fork)       │
│                                                                     │
│  Chain: scout → planner → worker → reviewer                        │
│  Parallel: workers with worktree isolation                          │
│  Model: openrouter/owl-alpha (all roles, always free)               │
│  cwd: /root/t1d, context: fork, concurrency: 2                     │
│                                                                     │
│  1. Mark in_progress  2. Dispatch  3. Verify  4. Mark complete     │
│  5. Create blocker todos for failures                               │
│  ✦ Never rely on completion prose alone — check git status          │
│                                                                     │
│  /subagents-doctor — diagnostics                                    │
│  /run worker "task" — dispatch                                      │
│  /chain scout -> planner -> worker — pipeline                       │
│                                                                     │
│  Installed from: npm:pi-subagents (nicobailon)                      │
│  Docs: https://github.com/nicobailon/pi-subagents                   │
└─────────────────────────────────────────────────────────────────────┘
```
