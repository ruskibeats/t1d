# Prompt: Customize Clanker Ops UI

Use when the user asks to change board colors, glyphs, columns, layout, context output, or terminal rendering.

## Instruction

Make focused UI changes that preserve Clanker Ops' operational style. Keep the board compact, readable, keyboard/terminal friendly, and consistent with the color router.

## Before Editing

Inspect:

- `/root/.pi/agent/extensions/todo/index.ts`
- `/usr/local/bin/clanker-board`
- `.pi/CLANKER_OPS_COLOR_SCHEMA.md` if present

## Color Rules

Use centralized color/status routing. Do not scatter one-off ANSI logic through renderers.

Visual precedence:

1. Failed
2. Blocked
3. Sent or active
4. Duplicate
5. Section default
6. Priority tags

Known semantic colors:

- Red: failed or P0.
- Orange: P1 or no-plan.
- Amber: reminder or Don't Forget.
- Green: P2.
- Cyan: blocked or active owner/handoff emphasis.
- Purple: duplicate.

Owner-specific styling should style only the visible owner characters, not the padded cell.

## Layout Rules

- Keep columns elastic where possible.
- Preserve alignment with ANSI-aware width helpers.
- Never slice ANSI escape sequences during truncation.
- Keep one horizontal line below column headers.
- Keep the footer separated by a horizontal line.
- Keep the legend compact.
- Do not add heavy vertical separators unless the user asks.

## Verification

After changes, run:

```bash
node --check /root/.pi/agent/extensions/todo/index.ts
clanker-board
clanker-board --context-only
```

If possible, reload Pi and inspect `/clanker`.
