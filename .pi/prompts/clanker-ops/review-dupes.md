# Prompt: Review Possible Duplicate Clanker Items

Use when the user asks to compare tasks, merge duplicates, explain differences, or rename items.

## Instruction

Compare the specified Clanker Ops items. Recommend whether they should be merged, renamed, or kept separate. Do not delete or merge without user confirmation unless the user explicitly asks for the action.

## Review Criteria

- Same intended outcome.
- Same affected files or area.
- Same owner.
- Same priority.
- Same plan content.
- Same blocker/dependency chain.
- Same user-facing result.

## Output Shape

```text
Review: #<a> and #<b>

Recommendation: merge | rename | keep separate

Why:
- <reason>

Suggested title(s):
- #<a>: <title>
- #<b>: <title>

Plan handling:
- Keep: #<id>_plan.md
- Merge notes from: #<id>_plan.md
```

## Rules

- If scopes differ, keep both and clarify titles.
- If one is clearly stale, recommend merge into the fresher item.
- If both have useful plans, preserve the better plan and copy unique notes.
- Use duplicate visual status where supported.
