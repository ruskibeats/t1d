# Clanker Ops #12: [SPRINT] Sprint 4: Code Quality + Provider Showcase

Status: pending
Owner: @worker
Tags: #p1 #backend #quality
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #12 is still open, assigned to you, and not blocked.
- Mark #12 in progress before implementation work.
- Read the full plan before editing files.

### While Working
- Keep changes scoped to this task and preserve unrelated user changes.
- Do not create skills, tools, scripts, or extra files unless the operator explicitly requested them or this plan names them.
- If you discover blockers, duplicates, missing context, or follow-up work, add/update Clanker Ops items instead of burying findings in prose.
- If the task cannot be completed, leave it in progress or mark it failed/deferred with a clear reason.

### Before Closing
- Run relevant verification checks.
- Update the Clanker Ops item with a completion summary.
- Include files changed, commands run, verification result, blockers/follow-ups, and estimated token burn.
- Mark the task completed only when the requested work is done and verified.

### Closeout Report Template

```text
Summary:
Files changed:
Commands run:
Verification:
Follow-ups created:
Blockers:
Token burn estimate:
Status:
```

## Plan

## Task Plan

### Intended Outcome
- Deliver the requested outcome for: [SPRINT] Sprint 4: Code Quality + Provider Showcase; context: #backend #quality #p1.
- Treat the preserved previous plan as source notes, not as permission to broaden scope.

### Likely Files, Modules, Or Commands
- Review the preserved previous plan notes below.
- Inspect the current project state and relevant files before editing.

### Steps
1. Confirm the task is still valid, assigned correctly, and not blocked.
2. Review the preserved previous plan notes and convert them into concrete execution steps.
3. Inspect relevant code, data, docs, or external systems before editing.
4. Make the smallest useful change that satisfies the task.
5. Update Clanker Ops if scope, blockers, duplicates, or follow-ups are discovered.
6. Prepare the closeout report before marking the task complete.

### Verification
- Run the narrowest relevant checks and report exact commands/results.
- If verification cannot be run, explain why and identify residual risk.

### Blockers, Dependencies, Or Questions
- Review preserved notes for blockers, dependencies, unanswered questions, or `none`.

### Closeout Notes
- Use the Closeout Report Template from the Execution Protocol.

### Preserved Previous Plan

From SPRINT_PLAN.md:
- S4-01: Service method naming consistency (create/list/get/delete across 16 domains)
- S4-02: Add missing __init__.py files (16 domain packages)
- S4-03: Garmin webhook end-to-end (push data → activity_entries/sleep_entries)
- S4-04: Connected devices UI (Settings page with provider status)
- S4-05: Warning cleanup (Pydantic V2, SQLAlchemy deprecations)
