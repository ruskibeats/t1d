---
name: "implement-scrollable-clanker-overlay"
description: "Add scrollable overlay board to Clanker Ops with up/down navigation, line limiting, and scroll position indicator"
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

- Adding scrollable TUI overlay to Clanker Ops board
- Need to limit display to N lines with navigation for remaining items
- Working with Pi extension TUI overlay components

## Procedure

1. **Create scrollable board component** (`view/scrollable-board.ts`):
   - Import existing board rendering logic
   - Add `maxLines` constant (e.g., 20)
   - Track `scrollOffset` state (0-indexed)
   - Slice tasks array: `visibleTasks = tasks.slice(scrollOffset, scrollOffset + maxLines)`
   - Render with scroll indicator: `${current}/${total}` or scrollbar visualization

2. **Update router.ts**:
   - Fix typo: `handlers` → `handler` if present
   - Add `handleOverlay` function with UI check
   - Register in handler record

3. **Add command help text**:
   - Update help string with `/clanker overlay` entry

4. **Verify**:
   - `/clanker overlay` launches in interactive mode
   - Arrow keys navigate (up/down)
   - Lines capped at limit

## Pitfalls

- Edit tool requires `edits` array format, not `newText` directly
- TUI Component interface needs `render(width)` method returning string[]
- Variable naming typos (`handlers` vs `handler`) cause runtime failures

## Verification

- Overlay launches and shows exactly maxLines rows
- Scroll indicator updates correctly
- Up/down arrows change position