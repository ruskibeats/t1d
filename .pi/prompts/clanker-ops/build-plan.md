# Prompt: Build Or Improve A Clanker Plan

Use when the user asks for a better plan, asks to plan task `#id`, or dispatches a planner.

## Instruction

Build a concise implementation plan for the specified Clanker Ops task. The plan should act as both a task plan and a worker instruction manual.

## Required Top Matter

Include this near the top of the plan:

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

## Required Sections

- Intended outcome.
- Relevant context.
- `## Task Plan` with these core headings:
- `### Intended Outcome`
- `### Likely Files, Modules, Or Commands`
- `### Steps`
- `### Verification`
- `### Blockers, Dependencies, Or Questions`
- `### Closeout Notes`
- Closeout template.

## Closeout Template

```md
## Closeout

- Status:
- Summary:
- Files changed:
- Commands/checks run:
- Result:
- Token/cost notes:
- Residual risk:
- Follow-ups:
```

## Planning Rules

- Prefer concrete commands and paths over vague wording.
- Do not over-plan unrelated improvements.
- If code changes are not required, say so clearly.
- If the task is just queue capture, keep the plan small.
- If the task is agent dispatch, make the expected output unambiguous.
- Leave plan review state unset unless the plan has been through the review gate.
- Do not add `#plan-reviewed` or `#ready-to-execute` while merely drafting a plan.
