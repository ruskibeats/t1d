# Clanker Ops #88: [iOS-04] Flutter scaffold — create project, theme, navigation

Status: pending
Owner: @dad_웃
Tags: #dad #flutter #ios
Branch: dad_1805
Blocked by: #86, #87

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #88 is still open, assigned to you, and not blocked.
- Mark #88 in progress before implementation work.
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
- Deliver the requested outcome for: [iOS-04] Flutter scaffold — create project, theme, navigation; context: #ios #flutter #dad.
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

## Intended Outcome
Flutter project scaffolded with Cupertino theme + nav.

## Step-by-Step
1. `flutter create --org com.yourapp`
2. Set bundle ID + team from #85
3. Build ThemeData from #87 tokens
4. Set up CupertinoApp with routing
5. Create stub screens

## Verification
`flutter run -d ios` launches with theme.

## Skills/Tools Required
- `flutter-theming-apps` -> `.agents/skills-archive/flutter-theming-apps/SKILL.md`

## Audit (EOD Report-Back)
Append findings to .pi/EOD_AUDIT.md: (1) files changed, (2) verification results, (3) gaps/findings, (4) decisions, (5) estimated tokens.
