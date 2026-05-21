---
name: "extension-context-doc"
description: "Create or update a CONTEXT.md domain glossary for a Pi extension in the T1D project. Documents core entities, state machines, CLI commands, metadata fields, and validation rules in a structured format. Use after creating, refactoring, or onboarding to a Pi extension that manages stateful entities."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Extension Domain Glossary (CONTEXT.md)

Create or update a CONTEXT.md domain glossary for a Pi extension in the T1D Companion project. Documents core entities, state machines, commands, and metadata fields in a structured format.

## When to Use

- After creating or significantly refactoring a Pi extension
- When the extension manages entities with lifecycle states and transitions
- When the extension has multiple commands with specific syntax
- When onboarding new developers to an extension codebase
- The glossary belongs at `.pi/extensions/<name>/CONTEXT.md`

Do NOT use this for:
- README-style user documentation — that goes in README.md
- Architecture Decision Records — those go in `docs/adr/`
- API endpoint documentation — that goes in the FastAPI OpenAPI spec

## Procedure

### 1. Identify Core Concepts

List the primary entities the extension manages. Each concept should have:
- **Name** (bolded)
- **One-paragraph definition** explaining what it is and its role
- **Relationships** to other concepts

```
### Task
A unit of work tracked by Clanker Ops. Tasks have an ID, status, subject,
and optional metadata. They represent user intentions translated into
actionable items.

### Dispatch
The act of sending a task to an AFK agent for execution...
```

### 2. Document the State Machine

Two sub-sections:

**Status Values**: Enumerate every possible state with a brief description.
```
### Status Values
- **pending** — Task is queued, ready for assignment
- **in_progress** — Task is assigned or actively being worked
- **completed** — Task finished successfully
- **deleted** — Task removed (tombstone status)
```

**State Transitions**: Show valid transitions between states. Use a bulleted list or matrix format.
```
pending → in_progress → completed
       → failed
       → cancelled
       → deferred
       → deleted

in_progress → pending
           → completed
           → failed
```

### 3. Document Commands

List every CLI command the extension supports, with:
- **Syntax** in code blocks
- **Description** of what it does
- **Example** usage

```
- `/clanker` — Show work board
- `/clanker dispatch #<id>` — Dispatch task to agent
- `/clanker eod` — End-of-day report
```

### 4. Document Metadata/Data Fields

For every entity that carries metadata (beyond core identity fields), list:
- **Field name** in code format
- **Type** and **Description**
- **Optional/Required**

```
- **dispatchRunId** — Links task to background execution
- **dispatchedAt** — ISO timestamp of dispatch initiation
- **dispatchAgent** — Name of the agent used
```

### 5. Document Validation Rules

Include any cross-entity validation rules:
```
### Task Dependencies
Tasks can declare `blockedBy` references to other task IDs.
The system validates that:
- Referenced tasks exist
- Referenced tasks are not deleted
- No cycles are created in the dependency graph
```

### 6. Write the File

Save as `CONTEXT.md` at the extension root:
```
.pi/extensions/<name>/CONTEXT.md
```

Start with a `# Extension Name — Domain Glossary` header and organize sections as:
1. `## Core Concepts`
2. `## Status Values` (only if entity has state lifecycle)
3. `## State Transitions` (table or list format)
4. `## Task Dependencies` (or entity relationships)
5. `## Metadata Fields` (data schema)
6. `## Commands` (CLI surface)

## Pitfalls

- **Don't confuse with user docs** — CONTEXT.md is for developer onboarding and agent context, not end-user help
- **Keep state transitions accurate** — Every listed transition should be enforced in code. Stale transitions are worse than no documentation
- **Don't skip validation rules** — Relationship and dependency rules are the most looked-up content
- **Update on every change** — Add a TODO to update CONTEXT.md as part of every feature branch if entities or commands change
- **Avoid implementation details** — Focus on concepts & contracts, not internal code structure

## Verification

- [ ] CONTEXT.md exists at `.pi/extensions/<name>/CONTEXT.md`
- [ ] All core entities are documented with definitions
- [ ] If entities have states, Status Values + State Transitions sections exist
- [ ] Every CLI command is listed with syntax
- [ ] Metadata fields are documented with types
- [ ] Validation/relationship rules are documented
- [ ] No stale or incorrect transition rules (cross-check against code)
- [ ] README.md or index.ts refers to CONTEXT.md for domain details