# Clanker Ops #10: [SPRINT] Sprint 2: Frontend Screen Consolidation

Status: completed
Owner: @builder
Tags: #p1 #frontend #ui
Branch: dad_1805

## Execution Protocol

### Before Starting
- Run `clanker-board --context-only` from the project root to load current queue context.
- Confirm #10 is still open, assigned to you, and not blocked.
- Mark #10 in progress before implementation work.
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
- Deliver the requested outcome for: [SPRINT] Sprint 2: Frontend Screen Consolidation; context: #frontend #ui #p1.
- Treat the preserved previous plan as source notes, not as permission to broaden scope.

### Likely Files, Modules, Or Commands
- Review the preserved previous plan notes below.
- Inspect the current project state and relevant files before editing.

### Steps
1. Confirm the task is still valid, assigned correctly, and not blocked.
2. Review the preserved previous plan notes and convert them into concrete execution steps.
3. Inspect relevant code, data, docs, or external systems before editing.
4. Execute sprint subtasks in order: S2-01 through S2-08.
5. Update Clanker Ops if scope, blockers, duplicates, or follow-ups are discovered.
6. Prepare the closeout report before marking the task complete.

### Execution Strategy
This sprint is too large for a single pass. Break into 8 subtasks and execute sequentially:
- S2-01: Chat.tsx → HootHolla.tsx (rename, add mic/camera/barcode, prompt chips)
- S2-02: FoodLog.tsx → 4-step Meal Review flow (Capture → Analysing → Review → Memory)
- S2-03: Patterns.tsx → card-led layout with Good/Worth watching/Needs attention grading
- S2-04: New Coach.tsx (progress streaks, gentle achievements)
- S2-05: New Memory.tsx (observations, voice notes, clinic notes)
- S2-06: New Discuss.tsx (share with caregiver/clinician)
- S2-07: Update App.tsx routes + Layout.tsx nav to match new structure
- S2-08: Copy pass — replace marketing language with plain English across all pages

### Verification
- Run `npx tsc --noEmit` — expected: 0 errors
- All new pages use existing design system (oklch colors, Card/Button components)
- Nav consolidated from 15 to 10 core items

### Blockers, Dependencies, Or Questions
- None

### Closeout Report

```text
Summary: Sprint 2 Frontend Screen Consolidation complete. 8 subtasks executed.
Files changed:
  - src/pages/HootHolla.tsx (NEW — mic/camera/barcode, prompt chips, cleaner layout)
  - src/pages/FoodLog.tsx (REWRITTEN — 4-step Meal Review flow)
  - src/pages/Patterns.tsx (REWRITTEN — card-led, Good/Worth watching/Needs attention)
  - src/pages/Coach.tsx (NEW — streaks, achievements, weekly insight)
  - src/pages/Memory.tsx (NEW — observations, questions, clinic notes, voice note)
  - src/pages/Discuss.tsx (NEW — share with doctor/caregiver, mark for review)
  - src/App.tsx (updated routes: /chat→HootHolla, /coach, /memory, /discuss)
  - src/components/Layout.tsx (updated nav: 10 core items)
  - src/hooks/useInsights.ts (fixed pre-existing </write_to_file> artifact)
Commands run:
  - npx tsc --noEmit (clean, 0 errors)
Verification:
  - TypeScript compiles cleanly
  - All new pages follow the design system
  - Nav consolidated from 15 to 10 core items
  - Plain-English copy throughout
Follow-ups created: None
Blockers: None
Token burn estimate: ~120K
Status: completed
```
