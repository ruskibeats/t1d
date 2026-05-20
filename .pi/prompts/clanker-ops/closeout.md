# Prompt: Close Out Clanker Work

Use when a worker finishes a Clanker Ops task.

## Instruction

Close the task cleanly. Update Clanker Ops state, preserve useful handoff context, and give the operator a concise summary.

## Required Closeout

```md
## Closeout

- Status: completed | failed | blocked | cancelled | deferred
- Summary:
- Files changed:
- Commands/checks run:
- Result:
- Token/cost notes:
- Residual risk:
- Follow-ups:
```

## Completion Rules

- Mark task `completed` only after verification or a clear explanation of why verification was not possible.
- If the task failed, mark it failed and include the reason.
- If blocked, record blockers and use `blockedBy` where appropriate.
- If follow-up work is needed, add new Clanker Ops items rather than burying them in prose.
- Do not delete the task or its plan unless the user asks.

## Good Final Response

```text
Closed #<id>.
Summary: <short result>
Verification: <commands/checks>
Follow-ups: <new ids or none>
```
