# Clanker Ops #86: [iOS-02] Dev machine — Xcode + Flutter SDK + CocoaPods

Status: deferred
Owner: @tom_웃
Tags: #ios #setup #tom
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #86 is still open, assigned to you, and not blocked.
- Mark #86 in progress before implementation work.
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
- Deliver the requested outcome for: [iOS-02] Dev machine — Xcode + Flutter SDK + CocoaPods; context: #ios #setup #tom.
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
Mac ready for Flutter iOS builds.

## Step-by-Step
1. Install Xcode from Mac App Store (you'll never open it)
2. Accept license: `sudo xcodebuild -license accept`
3. Clone Flutter: `git clone https://github.com/flutter/flutter.git -b stable`
4. Add to PATH, `flutter precache --ios`
5. `sudo gem install cocoapods`
6. `flutter doctor`

## Why Xcode?
You never open it. Flutter calls Xcode's toolchain behind the scenes:
- `flutter run` calls Xcode build system automatically
- `flutter build ipa` signs and archives via Xcode tools
- Only time you open Xcode: Organizer > Distribute App (30 secs)
Your workflow stays 100% in Flutter/VS Code.

## Skills/Tools Required
- `flutter-building-layouts` -> `.agents/skills-archive/flutter-building-layouts/SKILL.md`

## Audit (EOD Report-Back)
Append findings to .pi/EOD_AUDIT.md: (1) files changed, (2) verification results, (3) gaps/findings, (4) decisions, (5) estimated tokens.
