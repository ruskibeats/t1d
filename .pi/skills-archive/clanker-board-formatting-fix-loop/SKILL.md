---
name: "clanker-board-formatting-fix-loop"
description: "Fix terminal UI board formatting for Clanker Ops style boards: column width calcs, glyph legends, plan column display, owner coloring, compact mode, summary enhancements. Use when board has right-edge overflow, missing glyph legend, plan showing 'yes' instead of filename, or needs UX polish."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Clanker Board Formatting Fix Loop

## When to Use
When the Clanker Ops board has:
- Right-edge overflow (broken box-drawing chars)
- Plan column showing "yes" instead of filename
- Owner color spanning full column width
- Missing glyph legend
- Need for compact/summary/help view
- Title row text overflow

## Procedure

### 1. Diagnose the Issue
- Run `/clanker` and examine output visually
- Check if box-drawing chars are intact or broken
- Note column alignment and any truncation/spillover
- Note whether owner color spans full column or just the word

### 2. Column Width Calculation Fix
The critical formula in the board renderer:
```
available = inner - sum(spacing_gaps) - right_margin
```
- `inner = width - 2` (subtract left + right border chars)
- `spacing_gaps` = number of column gaps × gap width (e.g., 4 gaps × 2 chars each = 8 for 5 columns)
- `right_margin` = 1 (always add this)

Example (5 cols with icon/id/work/owner/plan):
- 4 gaps of 2 chars each = 8
- right margin = 1
- total non-data = 9
- work_column_width = remaining_width - (icon_w + id_w + owner_w + plan_w) - 9

### 3. Plan Column Display
- Don't check `task.description` — many tasks have no description
- Use deterministic filename: `#${task.id}_plan.md`
- Check if `.pi/todo-plans/` has the file via `existsSync`
- Display resolved filename or "no" as fallback

### 4. Owner Coloring (word-only)
- In `row()` function, apply color paint function to the individual cell value, not the padded string
- The paint function wraps `v` (the text), not `pad(v, width)`
- Example: `paint(text)` then `pad(result, target_width)`

### 5. Glyph Legend
Add a second line to the board's border line showing what each glyph means:
```
│ ○ pending  ◐ active  ! reminder  ⊘ blocked  ◌ deferred  ⇢ dispatched  ✗ failed  ⏱ long-running │
```

### 6. Enhanced Summary
Add counts for blocked, failed, no-plan, and long-running tasks below the header:
```
3 active · 12 queued · 2 blocked · 1 ⚠no-plan · 48 done
```

### 7. Compact Mode (`/clanker compact`)
- Strip non-essential columns (e.g., plan, last)
- Show only icon + ID + work + owner
- Fewer separator lines
- Useful for terminals narrower than ~80 chars

## Pitfalls
- **Race condition on reload**: presentBoard() returns groups struct; renderer references must use optional chaining (`groups.active?.length`) to survive EMPTY_STATE
- **Summary/title overflow**: The gap between title and summary must subtract summary length: `inner - title.length - summary.length`
- **Color paint on padded strings**: Always paint the raw text first, then pad the colored result — otherwise ANSI escape codes pad unevenly
- **process.stdout.columns fallback**: board.ts uses `process.stdout.columns || 120` but extensions reload may not have TTY; use a hardcoded minimum (72) as floor

## Verification
1. `/clanker` — board renders with intact box-drawing chars, no right-edge overflow
2. Plan column shows `#120_plan.md` not "yes"
3. Owner names colored, rest of column grey
4. Glyph legend visible in top section
5. `/clanker compact` — compact board renders
6. `/clanker help` — help text renders
7. Reload Pi — board renders on first render cycle without crash