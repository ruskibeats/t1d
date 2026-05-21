---
name: clanker-ops-plan-write
description: "Write a comprehensive Clanker Ops plan file with all required sections: Intended Outcome, Step-by-Step, Verification, Dependencies, Audit"
version: 1
created: 2026-05-19
updated: 2026-05-19
---
## When to Use

Use this when creating or updating a Clanker Ops plan file at `.pi/todo-plans/#N_plan.md`. Plan files auto-generated from the `description` field via `todo create` are NOT sufficient — they produce stub descriptions that lack the required sections. You MUST write full plans manually.

This also applies when a task is updated, re-scoped, or its plan is found to be a stub without the required sections.

## Required Plan Structure

Every `.pi/todo-plans/#N_plan.md` file MUST have these sections in order:

```markdown
# Clanker Ops #N: [TAG] Short subject line

Status: pending
Owner: @assignee
Tags: #tag1 #tag2
Branch: <branch-name>

## Intended Outcome

One paragraph describing what success looks like. Be specific about deliverables, states, or files produced.

## Step-by-Step

Numbered list of concrete actions. Each step should:
- Be specific enough to execute without guessing
- Reference exact file paths where applicable
- Referencing files to read/modify
- Reference commands to run where appropriate
- Be independently verifiable

## Verification

How to confirm the task is done correctly:
- Commands to run (e.g. pytest paths, curl endpoints)
- Files to check exist or contain expected content
- Conditions that must hold (e.g. "all tests pass", "no warnings")
- Edge cases to confirm

## Dependencies

- Non-blocking setup steps
- Prerequisite tasks or tickets (reference by #ID)
- External systems or credentials needed
- Blocked-by relationships

## Audit (EOD Report-Back)

Completed by the agent at task completion. Record:
- **Tokens consumed**: approximate total
- **Files changed**: list of modified/created files
- **Stages completed**: which steps were done
- **Stages deferred**: which steps remain (if any)
- **Unexpected issues**: blockers, wrong assumptions, or bugs encountered
- **Artifacts left behind**: temp files, worktrees, debug output
```

## Procedure

1. **Check if plan exists**: `ls .pi/todo-plans/#N_plan.md`
   - If it exists, read it to determine if it's a stub or full (stubs are <10 lines, missing the required sections)
   - If missing or a stub, proceed to write

2. **Gather task context**:
   - Read the task description from `todo get #N`
   - Read any upstream references (sprint plans, GRAPH_TODO.md, MASTER_TODO, etc.)
   - Read related plan files for blocked-by tasks
   - Understand the task's position in the overall workflow

3. **Write the plan**: Use the required structure above. Be specific about file paths, command invocation, and verification criteria. Avoid "detailed in" or "see above" — each section should be self-contained.

4. **Register the plan** (if creating for an already-existent task): Optionally update the task description to reference the plan: `"See .pi/todo-plans/#N_plan.md"`

## Verification

- The plan file has all 5 required sections: Intended Outcome, Step-by-Step, Verification, Dependencies, Audit
- Sections are populated with task-specific content (not template boilerplate)
- Step-by-Step references exact file paths and commands
- Verification includes runnable commands
- Audit section is present (populated at completion)

## Pitfalls

- **Do NOT use the `todo create --description` field as the plan**. The auto-generated stub is insufficient.
- **Do NOT skip the Audit section**. It must exist in the file from creation (populated later at completion).
- **Keep the plan focused on execution**. Avoid design exploration or architectural analysis that belongs in a separate document.
- **Reference exact file paths**, not relative-to-repo or vague locations.
- **For blocked-by tasks**, include the prerequisite #ID in the Dependencies section and the plan file's header BlockedBy section.
- **When updating an existing plan**, preserve any Audit content already written at task completion.