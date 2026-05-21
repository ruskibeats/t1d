# Clanker Ops — Domain Glossary

## Core Concepts

### Task
A unit of work tracked by Clanker Ops. Tasks have an ID, status, subject, and optional metadata. They represent user intentions translated into actionable items.

### Dispatch
The act of sending a task to an AFK (Away From Keyboard) agent for execution. A dispatch creates a subprocess that runs the agent's work independently.

### RunId
A unique identifier for a specific dispatch execution, formatted as `{timestamp}-{random}`. Used to correlate events between the main Pi session and background subagents.

### Plan File
A markdown file at `.pi/todo-plans/#N_plan.md` containing task details: Intended Outcome, Step-by-Step Plan, Verification criteria, Dependencies, and Audit trail.

### Intercom Event
A lifecycle notification from a background subagent, emitted when the run needs attention, is active, or has completed. Events include `needs_attention`, `active_long_running`, and `completion_guard`.

## Status Values

- **pending** — Task is queued, ready for assignment
- **in_progress** — Task is assigned or actively being worked
- **completed** — Task finished successfully
- **deleted** — Task removed (tombstone status)
- **failed** — Task failed during execution
- **cancelled** — Task cancelled before completion
- **deferred** — Task postponed, not currently actionable

## State Transitions

```
pending → in_progress → completed
       → failed
       → cancelled
       → deferred
       → deleted

in_progress → pending
           → completed
           → failed
           → cancelled
           → deferred
           → deleted

completed → failed
         → cancelled
         → deleted

failed → pending
      → in_progress
      → deleted

cancelled → pending
         → in_progress
         → deleted
```

## Task Dependencies

Tasks can declare `blockedBy` references to other task IDs. The system validates that:
- Referenced tasks exist
- Referenced tasks are not deleted
- No cycles are created in the dependency graph

## Metadata Fields

- **dispatchRunId** — Links task to background execution
- **dispatchedAt** — ISO timestamp of dispatch initiation
- **dispatchAgent** — Name of the agent used
- **outputPath** — Where dispatch results are written
- **autoSpawned** — Whether dispatch was auto-fired
- **lastAlert** — Latest intercom event type
- **lastHeartbeat** — Timestamp of last activity

## Commands

- `/clanker` — Show work board
- `/clanker dispatch #<id>` — Dispatch task to agent
- `/clanker eod` — End-of-day report
- `/clanker focus <filter>` — Filter board by tag/owner