---
id: 152
title: Extract command handlers from todo.ts
created: 2026-05-20
assignee: @architect
---

## Intended Outcome

Split command handling in `todo.ts` into separate, testable command modules.

## Step-by-Step

1. Create `commands/dispatch.ts` — Extract dispatch handler
2. Create `commands/eod.ts` — Extract EOD report handler  
3. Create `commands/help.ts` — Extract help handler
4. Refactor `todo.ts` to wire commands via `registerCommand()`
5. Add unit tests for each command handler

## Verification

- `/clanker dispatch #ID` works identically
- `/clanker eod` works identically
- `npm test commands/*.test.ts` passes