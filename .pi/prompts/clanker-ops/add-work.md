# Prompt: Add Work To Clanker Ops

Use when the user asks to add, remember, queue, or track work in Clanker Ops.

## Instruction

Add the user's request to Clanker Ops as a work item. Create or update a mini-plan. Do not implement the task yet unless the user explicitly asks you to do the work now.

## Required Behavior

1. Check whether a similar item already exists.
2. If it is clearly a duplicate, flag it or suggest a merge instead of silently creating another item.
3. Create the item with a clear title.
4. Add tags for priority, area, and type.
5. Add an owner only if the user specified one or the assignment is obvious.
6. Write a mini-plan that can guide a future worker.
7. Return the id, title, tags, owner, and plan path.

## Mini-Plan Shape

```md
## Execution Protocol

- Mark this task in progress before starting substantial work.
- Read this plan and inspect the relevant files before editing.
- Keep changes focused and preserve user changes.
- Run the verification checks below.
- Close out with summary, files changed, tests run, token/cost notes if available, and follow-ups.

## Task Plan

## Intended Outcome

## Likely Files, Modules, Or Commands

## Steps

## Verification

## Blockers, Dependencies, Or Questions

## Closeout Template
```

## Do Not

- Do not create skills.
- Do not create new tools.
- Do not create scripts.
- Do not implement the task.
- Do not write unrelated docs.
