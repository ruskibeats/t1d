---
name: "deepen-pi-extension-with-polish-iteration"
description: "Deepen a Pi extension's architecture using improve-codebase-architecture, then iteratively polish formatting with live user feedback. Covers CONTEXT.md creation, deepest-first module extraction, @ts-nocheck removal, board formatting tweaks (column widths, plan column, glyph legend, owner coloring), and user-verified fix loop."
version: 3
created: "2026-05-20"
updated: "2026-05-20"
---
# Deepen Pi Extension with Polish Iteration

## When to Use
After running `improve-codebase-architecture` (or similar) on a Pi extension and getting architecture findings that need implementation, especially when:
- The extension has `@ts-nocheck` files that need removal
- The extension has shallow modules (200+ lines mixing file I/O, business logic, and rendering)
- The extension has a TUI/CLI board or widget output that needs formatting polish

## Procedure
### Phase 4: Polish Iteration

1. After board.ts rewrite, run `/clanker` and inspect the rendered board visually
2. Common formatting bugs to check:
   - **Right-edge overflow**: Column widths must subtract spacing (e.g., `inner - totalSpacing - rightMargin`) — not just the sum of column widths. Total spacing = (columnCount-1)*2 for column gaps + 1 for right margin.
   - **Title row gap**: `inner - title.length - summary.length` (not just `inner - title.length`)
   - **Plan column**: Use deterministic filename like `#N_plan.md` via `getPlanRef()`, not a boolean `hasPlan` — boolean shows `yes`/`no` instead of the actual filename
3. Apply user's visual feedback — they may request:

   **Glyph legend system**: Add a `classifyVisual()` function returning `{ icon, paint, priorityLevel }` for each task. Use a closed set of Unicode glyphs with specific meanings:
   - `○` pending, `◐` in_progress, `!` reminder (dont-forget), `⊘` blocked, `◌` deferred
   - `⇢` dispatched/sent, `✗` failed, `⚠` needs-attention, `⧉` duplicate, `×` cancelled, `⏱` long-running
   - Order icons so most specific checks (failed, dontForget, dispatched, blocked) come before generic ones (in_progress, pending)
   - Render a color legend + glyph legend in the board footer as two separate rows

   **Relative time formatting**: In the Last column, show progressive detail levels:
   - `< 1 minute`: `"just now"`
   - `< 1 hour`: `"Xm ago"` (e.g., `5m ago`)
   - `< 24 hours`: `"Xh ago"` (e.g., `2h ago`)
   - Same calendar day: `"HH:MM"` (e.g., `11:48`)
   - Older: `"MM-DD"` (e.g., `05-20`)
   - No activity: `"-"`
   - Use `getLatestActivity()` that checks multiple timestamp fields (handoff.sentAt, planHandoff.sentAt, dispatchedAt, updatedAt) and picks the latest

   **ActiveForm display**: For `in_progress` tasks, append the `activeForm` value as a parenthetical in the work column (e.g., `"Build login (writing tests)"`). Use `ansi.gray("(activeForm)")` so it's visually distinct from the task name.
   - **Pitfall**: After plan generation or dispatch, `activeForm` may carry over stale values from previous work. The renderer must handle empty/null activeForm gracefully.

   **Compact mode**: A `/clanker compact` board variant (no borders, indentation-based) for narrow terminals. Structure:
   - Header line with summary counts
   - `Active:` section — each line: `◐ #N title (activeForm) @owner 5m ago`
   - `Failed:` section — each line: `✗ #N title`
   - `Reminders:` section — each line: `! #N title`
   - `Queued:` section — first 10 tasks, each line: `○/⊘ #N title @owner`, with `"... N more"` overflow
   - `Done:` section — just a count line
   - No borders, no column alignment, no ANSI column width math

   **Enhanced summary counts**: In the board title row, compute fresh counts from the raw task array (not from `presentBoard` results):
   - Active count, queued count, failed count (red), blocked count (cyan), done count, no-plan count (orange ⚠)
   - **Pitfall**: Summary counts must be computed from the raw `tasks` array, not from `board.groups`. The `presentBoard()` function may classify tasks differently (e.g., dontForget tasks are in their own group, not queued). The summary should always reflect the full set.

   **Owner span-only coloring**: When coloring the owner column, use a `spanOnly` pattern:
   - Define a `getOwnerPaint()` function that returns a color function for specific owners (e.g., `@dad_웃` → blue bg, `@tom_웃` → green bg)
   - In the cell renderer, if `spanOnly` is true, apply the paint function only to the text, not to the padding whitespace
   - This prevents the entire column from being colored, keeping the board clean

4. After each change, visually verify with `/clanker` and iterate. Track remaining bugs in a checklist.

### Phase 5: Enhancement (if requested)

After basic deepening + polish is stable, implement features:
1. Board context injection (HTML comment with live state summary)
2. Auto-plan generation on dispatch when plan file missing
3. `/clanker bulk` command for batch task creation across multiple IDs (e.g., `/clanker bulk #10,#11,#12 --status in_progress`)
4. Dispatch history log (`/clanker log` — structured audit trail in `.pi/dispatch-log.json`)
5. Compact mode (`/clanker c` or `/clanker compact` — shows more tasks per screen without borders)
6. Agent registry for mapping `@owner` names to structured agent definitions
## Pitfalls
- **write on existing files DESTROYS content** — always use `edit` for updating plan files or existing modules
- **`content` not `contents`** — the `write` tool parameter is `content` (singular)
- **`todo` tool doesn't accept `action: "complete"`** — use `action: "update"` with `status: "completed"`
- **Board column math**: The inner width must account for ALL spacing chars (e.g., 4 column gaps × 2 chars = 8, plus 1 right margin = 9 total padding). A column that is `inner - 65` works on one board but not another — always calculate based on actual column spacing.
- **Plan column trap**: Don't store a boolean `hasPlan` in the view model — the renderer will show `yes`/`no`. Store the actual filename string like `#120_plan.md`.
- **Summary count freshness**: When computing enhanced summary counts (active/failed/blocked/no-plan), do NOT use data from `presentBoard()` result groups. Compute counts directly from the raw `tasks` array, because `presentBoard()` classifies tasks into groups (e.g., dontForget is separate from queued) and may not reflect the full set.
- **activeForm stale carry-over**: After plan generation, dispatch, or status transition, `activeForm` may carry over from previous werk. The renderer must handle empty/null `activeForm` gracefully — only show `(activeForm)` when non-empty, and explicitly clear `activeForm` after plan generation.
- **Icon classification ordering**: In `classifyVisual()`, check most specific conditions FIRST (failed, long-running, dontForget, dispatched, sent, blocked, duplicate) before generic ones (in_progress, pending, deferred, cancelled). If you check `in_progress` first, a dispatched task that is also `in_progress` gets the generic `◐` icon instead of the specific `⇢` icon.
- **spanOnly owner coloring**: The `getOwnerPaint()` function must be paired with a `spanOnly` boolean in the cell renderer. Without it, the entire column width gets colored (including padding whitespace), making the board look messy. The pattern: `paint(text) + " ".repeat(padding)` vs `paint(pad(text, width))`.
- **Compact mode doesn't need column math**: Because compact mode is indentation-based (no `box`/`borderLine`/`pad` wrappers), it avoids all the column-width math bugs. This is a useful fallback when the full board has formatting issues.
- **Relative time edge cases**: `formatLastRan()` must handle NaN dates (invalid timestamps), dates in the future (negative diff), and empty timestamp fields. Always filter with `!Number.isNaN(d.getTime())` and sort descending.
- **Update callers in same commit**: When you change a module's signature (e.g., `renderClankerBoard` now receives `Task[]` instead of reading files internally), update ALL callers in the same commit or the extension breaks.
## Verification
- [ ] Zero `@ts-nocheck` files in the extension
- [ ] `/clanker` renders with no right-edge overflow
- [ ] Plan column shows filenames (not `yes`/`no`)
- [ ] Owner column colors only the name text, not the full column width
- [ ] All callers import from the correct new paths
- [ ] `tsc --noEmit` passes (or compile check succeeds)
- [ ] Git commit history is clean and well-structured