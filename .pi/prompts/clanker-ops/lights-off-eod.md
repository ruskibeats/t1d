# Prompt: Lights Off And End-Of-Day

Use for end-of-turn, end-of-day, shutdown, or housekeeping review.

## Lights Off

Lights Off is a non-mutating checklist. It should show pending unassigned housekeeping items and the exact dispatch command to run when ready.

Eligible items:

- Tags: `#remember`, `#dont-forget`, `#chore`, `#ops`, `#housekeeping`
- Or text matching: push, commit, git, save memory, checkpoint, deploy, backup, cleanup, document

Do not dispatch automatically.

## Lights Off Output

```text
Lights Off

#<id> <item>
Tags: <tags>
Plan: <plan or no>
Suggested: /clanker dispatch #<id>
```

If empty:

```text
Lights off: nothing pending.
```

## End-Of-Day Report

When asked for an end-of-day report, summarize existing Clanker Ops state. Do not create a skill or tool.

Include:

- Completed today or recently completed.
- Active or dispatched work.
- Queued P0/P1 items.
- Blocked items.
- Don't Forget items.
- Recommended next actions.

If the user asks to add end-of-day reporting to Clanker Ops, add a queued work item and mini-plan. Do not generate a skill unless explicitly asked.
