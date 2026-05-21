---
name: clanker-assignee-mismatch-resolution
description: Detect and resolve assignee mismatches between the Clanker Ops board and CLANKER_ROSTER.md. Use when a task's board assignee differs from the roster entry, or when reconciling task ownership across multiple sources of truth.
version: 1
created: 2026-05-19
updated: 2026-05-19
---
# Clanker Assignee Mismatch Resolution

Resolve discrepancies between the Clanker Ops task board assignee and the CLANKER_ROSTER.md documented assignee for a given task.

## When to Use

- A task's board assignee (visible via `todo list` or `todo get`) differs from its entry in CLANKER_ROSTER.md
- A task needs to be reassigned and the correct owner must be validated against the roster
- Reconciling ownership after a task was handed off, dispatched, or moved between agents
- Auditing all tasks for assignee drift between board and roster

**Do not use** when:
- The task has no roster entry (not yet tracked in the roster) — use `clanker-roster-agent-registration` to add it first
- You're only adding or updating the roster document itself without reference to a board task

## Procedure

### 1. Identify the target task

```
todo get <id>
```

Record the current `assignee` field from the board output.

### 2. Read the roster entry

Read `docs/CLANKER_ROSTER.md` and find the task by ID number (look for the `#ID` column or task title).

If the task is listed, note the `assignee` column value (e.g., `@researcher`, `@dad_웃`, `@builder`).

### 3. Compare board vs roster assignees

| Case | Action |
|------|--------|
| Match | No action needed. State the match. |
| Mismatch | Continue to step 4. |
| Missing from roster | Suggest adding it via `clanker-roster-agent-registration`. |
| Stale roster entry (task completed, still listed) | Flag for roster cleanup. |

### 4. Determine the correct assignee

Consider:
- **Roster as source of truth for planned allocation** — the roster reflects the documented assignment intent
- **Board as source of truth for current reality** — the board reflects who is actually working it now
- **Task subject and description** — does the work match the assignee's specialty (researcher for investigation, builder for implementation, human `웃` for oversight)?

Convention from CLANKER_ROSTER.md:
- `@researcher` — investigation/scoping
- `@builder` — implementation
- `@scout` — discovery/audit
- `@planner` — planning
- `웃` suffix — human owner
- Droid assignees use `warning` (amber) color; human assignees use `accent` (cyan/highlight)

### 5. Reassign using todo tool

```
todo update <id> assignee="<correct_assignee>"
```

Confirm the update by re-reading the task:

```
todo get <id>
```

### 6. Optionally update the roster

If the mismatched roster entry reflects an outdated plan (e.g., task was supposed to be `@researcher` but actually needs `@builder`), update the roster to match reality using `clanker-roster-agent-registration`.

## Pitfalls

- **Roster may be stale.** CLANKER_ROSTER.md is a planning document that may not reflect live reassignments. The board is the source of truth for *current* state; the roster is the source of truth for *intended* allocation. Both can be "wrong" — use judgment.
- **Self-referential blockedBy.** When moving/reassigning, do not set `blockedBy` to the task's own ID — the tool rejects it with an error.
- **Droid vs human assignee.** Droid assignees (`@researcher`, `@builder`) handle focused execution; human `웃` suffix assignees provide oversight. Mixing them carelessly can cause integrity violations per the roster's integrity rules: "Agents must never change task assignees."
- **Do not clobber.** When reassigning, preserve any existing labels/tags and branch info unless updating them intentionally.
- **Send/dispatch doesn't auto-update status.** If using `todo send` or `todo dispatch`, the handoff creates a "sent" record but the task status stays `pending`. You may need to manually update status to `in_progress` after dispatch.

## Verification

1. `todo get <id>` shows the correct `assignee` field
2. The roster entry (if it exists) now matches the board, or you've consciously decided to update it
3. The task's labels/tags and branch info are preserved or appropriately updated
4. If the task was dispatched/sent, status reflects active work (not just `pending`)