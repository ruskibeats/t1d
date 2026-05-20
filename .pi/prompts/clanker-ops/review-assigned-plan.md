# Prompt: Review Assigned Clanker Plan

Use when the user asks whether a Clanker Ops task plan is ready for an assigned clanker, asks to review a plan before dispatch, or asks whether an owner has enough instruction to act.

## Instruction

Review the specified Clanker Ops task and its plan. Decide whether the assigned clanker can safely execute it without guessing. Do not implement the task. Do not create skills, tools, scripts, or unrelated files.

Use the `grill-me` skill as the review method before marking a plan ready. Treat it as a plan stress-test: challenge assumptions, resolve decision branches, inspect the codebase for questions that can be answered locally, and only ask the operator about genuinely unresolved decisions.

After review, update the plan being reviewed in place. If the plan is ready for execution, put the task back into the queue with review tags such as `#plan-reviewed` and `#ready-to-execute`. If the plan is not ready, do not add ready tags; leave clear required fixes instead.

## Inputs To Inspect

- Task record in `.pi/todo-state.json`
- Plan file at `.pi/todo-plans/#<id>_plan.md`
- Current board state via `/clanker` or `clanker-board`
- Relevant nearby plans only if needed for dependencies or duplicate checks

## Review Criteria

Check whether the task has:

- Clear title and intended outcome.
- Sensible owner for the work type.
- Correct priority and tags.
- Plan file present and referenced.
- Execution protocol near the top.
- `## Task Plan` section present.
- `### Intended Outcome` heading present and specific.
- `### Likely Files, Modules, Or Commands` heading present.
- `### Steps` heading present with concrete actions.
- `### Verification` heading present with checks.
- `### Blockers, Dependencies, Or Questions` heading present.
- `### Closeout Notes` heading present.
- Closeout template.
- No instruction to create skills/tools/scripts unless explicitly required.
- No broad or unrelated scope creep.
- No obvious duplicate or merge conflict with another Clanker Ops item.

## Grill-Me Review Gate

Before deciding `ready to dispatch`, run the plan through a grill-me style review:

- What assumption would make this plan fail?
- What context is missing for the assigned owner?
- What should the worker inspect before editing?
- What exact output proves the work is done?
- What should not be changed?
- What blockers, dependencies, or duplicate tasks could derail execution?
- Can unanswered questions be answered by reading the codebase or board state?

If the grill finds fixable gaps, update the same plan file before returning the task to the queue.

If the grill finds unresolved operator decisions, mark the decision as `needs plan improvement` or `blocked`, and list the exact questions.

## Owner Fit

Use these defaults when judging assignment:

- `@planner` - creates or improves plans.
- `@worker` - implementation.
- `@builder` - product or feature build work.
- `@scout` - exploration, discovery, unknown-codebase inspection.
- `@researcher` - research, analysis, external context.
- `@reviewer` - code or plan review.
- `@fixer` - focused bug fixing.
- `@clanker` - general queue handling and housekeeping.
- `@name_웃` - human-owned work.

If the owner does not fit, recommend reassignment but do not change it unless asked.

## Decision Labels

Return exactly one primary decision:

- `ready to dispatch`
- `needs plan improvement`
- `wrong owner`
- `blocked`
- `duplicate/merge candidate`
- `too broad`

## Ready Tagging

When and only when the plan is ready:

- Add or recommend adding `#plan-reviewed`.
- Add or recommend adding `#ready-to-execute`.
- Remove or recommend removing `#needs-plan-review` if present.
- Keep existing priority/area tags.

If using the Clanker Ops tool directly, update the existing task. Do not create a replacement task.

## Output Shape

```text
Plan Review: #<id> <title>

Decision: <decision label>

Owner fit:
- Current owner: <owner or unassigned>
- Recommendation: <keep/reassign to @owner>

What is good:
- <short bullets>

What is missing or risky:
- <short bullets>

Required fixes before dispatch:
- <short bullets or none>

Suggested plan patch:
- <exact section-level changes, not a full rewrite unless needed>

Queue update:
- <tags/status/owner changes made or recommended>

Dispatch readiness:
- <one sentence>
```

## If Updating The Plan Is Requested

If the user explicitly asks you to fix the plan, update the plan file only. Keep the patch focused.

If the review makes the plan ready and the user allows queue updates, update the existing task tags with `#plan-reviewed` and `#ready-to-execute`.

Required top section:

```md
## Execution Protocol

- Register this task on Clanker Ops as `in_progress` before starting substantial work.
- Read this plan and inspect the current code/state before editing.
- Keep edits focused on this task and preserve user changes.
- Do not create skills, tools, scripts, or unrelated files unless the user or this plan explicitly requires them.
- Update Clanker Ops if the task becomes blocked, duplicated, failed, cancelled, or deferred.
- Run the verification checks listed below.
- Close out the task with summary, changed files, checks run, token/cost notes if available, residual risk, and follow-up items.
```

## Do Not

- Do not implement the task during plan review.
- Do not dispatch the task unless the user asks.
- Do not create new queue items unless the review discovers a necessary follow-up and the user asks you to add it.
- Do not delete or merge duplicate tasks without confirmation.
