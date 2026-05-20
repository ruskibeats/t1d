# Clanker Ops #95: [OPS] Top up OpenRouter API account

Status: pending
Owner: @tom_웃
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #95 is still open, assigned to you, and not blocked.
- Mark #95 in progress before implementation work.
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
- Deliver the requested outcome for: [OPS] Top up OpenRouter API account.
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

## Intended Outcome\nOpenRouter account funded and API key working.\n\n## Step-by-Step\n1. Log in to openrouter.ai\n2. Check account balance / credit status\n3. Add funds via payment method\n4. Verify API key responds: `curl https://openrouter.ai/api/v1/auth/key`\n5. Update .env if key changed\n6. Run a test LLM call to confirm working\n\n## Verification\nSubagent dispatches work (tests pass, no 402/429 errors).\n\n## Skills/Tools Required\n- (none — human task, requires OpenRouter web dashboard)\n\n## Audit (EOD Report-Back)\nAppend to .pi/EOD_AUDIT.md: (1) new balance, (2) any key changes, (3) gaps/findings, (4) decisions, (5) estimated tokens.
