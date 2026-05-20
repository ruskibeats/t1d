# Clanker Ops #11: [SPRINT] Sprint 3: Security + Deployment Hardening

Status: pending
Owner: @dad_웃
Tags: #p1 #backend #deployment #security
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #11 is still open, assigned to you, and not blocked.
- Mark #11 in progress before implementation work.
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
- Deliver the requested outcome for: [SPRINT] Sprint 3: Security + Deployment Hardening; context: #backend #deployment #security #p1.
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
- S3-01: Add rate limiting (slowapi) - login 5/min, register 3/min, chat 30/min
- S3-02: Remove hardcoded demo login (env-var gated demo mode)
- S3-03: Dual-write verification tests (exercise/sleep/insulin → health_metrics)
- S3-04: API smoke test script (25 endpoints)
- S3-05: Demo data seeder (realistic multi-day data)
- S3-06: Production Docker compose (PostgreSQL, backend, frontend)
