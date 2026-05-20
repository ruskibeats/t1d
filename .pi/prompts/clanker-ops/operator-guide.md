# Clanker Ops Operator Guide

## Purpose

Clanker Ops is the project work queue and agent orchestration surface. It tracks work items, owners, tags, plans, dispatch state, blockers, reminders, and completion.

The queue is the source of truth. Plans are the instruction manuals for workers. Commands and tools should update the queue, not bypass it.

## Source Of Truth

- Board state: `.pi/todo-state.json`
- Plan files: `.pi/todo-plans/#id_plan.md`
- Pi board command: `/clanker`
- Terminal board command: `clanker-board`
- Hidden context for external agents: `clanker-board --context-only`

## Core Operating Rules

1. If the user asks to add work, create a Clanker Ops item and a mini-plan.
2. Do not create skills, tools, scripts, docs, or code unless explicitly asked.
3. If work needs deeper execution, write it into the task plan and let the assigned owner act from the plan.
4. If claiming a task, mark it `in_progress` before doing substantial work.
5. If dispatching a task, include the plan path, expected output, verification checks, and closeout requirements.
6. If finishing a task, close it with a concise summary, changed files, commands run, verification result, token/cost notes if available, and follow-up items.
7. If blocked, record `blockedBy` and explain the blocker in the plan or item description.
8. If a requested change is ambiguous, add a clear mini-plan instead of inventing broad new infrastructure.
9. Preserve user changes. Never clean up or delete queue data unless explicitly asked.
10. Treat Clanker Ops as operational infrastructure, not a generic todo app.

## Work Item Expectations

Every meaningful item should have:

- Clear title.
- Owner when known.
- Tags for priority, area, and type.
- Plan reference or `no` plan state.
- Mini-plan with intended outcome, likely files, steps, verification, blockers, and closeout notes.

## Recommended Tags

- Priority: `#p0`, `#p1`, `#p2`
- Area: `#backend`, `#frontend`, `#ios`, `#graph`, `#docs`, `#ops`, `#design`, `#test`
- Type: `#feature`, `#bug`, `#review`, `#audit`, `#chore`, `#remember`, `#housekeeping`
- State hints: `#blocked`, `#duplicate`, `#failed`

## Owners

Known agent-style owners include:

- `@clanker` - general queue handler
- `@planner` - planning work
- `@worker` - implementation work
- `@builder` - product or feature build work
- `@scout` - exploration and discovery
- `@researcher` - research and analysis
- `@reviewer` - review work
- `@fixer` - bug fixing

Human owners can use the project convention:

- `@dad_웃`
- `@tom_웃`
- Or another `@name_웃` human owner if accepted by the tool.

## Visual Semantics

Use color and glyphs as status language, not decoration.

- Red: failed or P0.
- Orange: P1 or missing plan.
- Amber: reminder, housekeeping, or Don't Forget.
- Green: P2 or low-risk work.
- Cyan: blocked or active handoff.
- Purple: duplicate.

Visual precedence should remain:

1. Failed
2. Blocked
3. Sent or active handoff
4. Duplicate
5. Section default
6. Priority tags

## Capture Behavior

When the user says:

- "add X to Clanker Ops"
- "put X on the board"
- "remember X"
- "make a todo for X"

Do this:

1. Create or update a Clanker Ops item.
2. Add appropriate tags.
3. Write or update the mini-plan.
4. Report the task id and plan path.

Do not do this unless asked:

- Create a new skill.
- Create a new command.
- Create a script.
- Edit unrelated docs.
- Start implementing the task immediately.

## Planning Standard

Plans should start with an execution protocol so workers know how to behave.

Required top sections:

1. `## Execution Protocol`
2. `## Task Plan`
3. `## Intended Outcome`
4. `## Likely Files, Modules, Or Commands`
5. `## Steps`
6. `## Verification`
7. `## Blockers, Dependencies, Or Questions`
8. `## Closeout Template`

The execution protocol should instruct the worker to:

- Register the task as in progress before execution.
- Read the plan and current code before editing.
- Keep edits focused.
- Preserve user changes.
- Run relevant checks.
- Close out with summary, files changed, tests, token/cost notes if available, and residual risk.

## Dispatch Behavior

Dispatch is explicit. If a user says "send #id to owner", use dispatch/send behavior.

The dispatch message should include:

- Task id and title.
- Owner.
- Plan path.
- Branch or working context if known.
- Expected output.
- Verification checks.
- Closeout requirements.

## Plan Review Gate

Use plan review before dispatch when the operator asks whether a task is ready for a clanker, when a task is high-risk, or when the plan looks thin.

Plan review should use the `grill-me` skill as a stress-test, then update the existing plan in place. The review should resolve assumptions, missing context, verification gaps, owner fit, blockers, duplicate risk, and non-goals.

When a plan passes review, tag the existing task with:

- `#plan-reviewed`
- `#ready-to-execute`

Do not add these tags while merely drafting a plan. Do not create a replacement task just to mark a plan reviewed.

## Duplicate Handling

When two tasks appear similar:

1. Compare title, tags, owner, plan, and intended outcome.
2. Decide one of:
   - Merge
   - Rename for clarity
   - Keep separate because scope differs
3. Preserve the better plan.
4. Mark duplicate candidates visually where supported.
5. Do not delete duplicates unless the user confirms.

## Don't Forget And Lights Off

Don't Forget is for housekeeping or end-of-turn reminders such as:

- Push to git.
- Commit changes.
- Save memory.
- Checkpoint state.
- Deploy.
- Backup.
- Cleanup.
- Document.

Lights Off is the active shutdown checklist. It should show pending unassigned housekeeping items and suggested dispatch commands. It should not mutate or dispatch by default.

## External Agent Context

For Cursor, Cline, or other agents outside Pi:

- Use `clanker-board` for the visible queue.
- Use `clanker-board --context-only` when the agent needs hidden operating context.
- Tell external agents to treat Clanker Ops as source of truth and not create project files unless the plan or user explicitly asks.

## Anti-Patterns

Avoid these unless explicitly asked:

- "I created a skill for that."
- "I wrote a helper script."
- "I generated a standalone tool."
- "I changed global agent memory."
- "I implemented the task while only being asked to add it to Clanker Ops."
- "I deleted or merged duplicate items without confirmation."

## Good Response Shape

When adding work:

```text
Added #123 to Clanker Ops: <title>
Plan: .pi/todo-plans/#123_plan.md
Tags: #p1 #area #type
Owner: @owner or unassigned
```

When finishing work:

```text
Closed #123.
Summary: <what changed>
Files: <key files>
Verification: <commands/checks>
Token/cost notes: <if available>
Follow-ups: <if any>
```
