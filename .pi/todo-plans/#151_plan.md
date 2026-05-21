---
id: 151
title: Split board.ts into grouping.ts + renderer.ts
created: 2026-05-20
assignee: @architect
---

## Intended Outcome

Separate concerns in `view/board.ts` into:
- `grouping.ts` — Pure task classification functions
- `board.ts` — Thin ANSI renderer calling classification

## Step-by-Step

1. Create `view/grouping.ts` with `classifyTask(item, allItems)` → `{ section, icon, paint }`
2. Extract `isDontForget`, `isDuplicate`, `groupItems` into grouping module
3. Simplify `visual()` function to use `classifyTask` result
4. Add unit tests for `classifyTask` (no ANSI parsing needed)
5. Verify board renders identically (visual regression)

## Verification

- `clanker list` output unchanged
- `npm test view/grouping.test.ts` passes (new file)
- `clanker list | wc -l` count matches before/after