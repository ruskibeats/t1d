---
name: "build-scrollable-tui-overlay"
description: "Build a scrollable TUI overlay widget with virtual scrolling for terminal interfaces. Use when creating overlay boards that need to handle large datasets within limited vertical space (e.g., 20 lines) with up/down navigation."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

- Creating a TUI overlay that displays many items in limited space (e.g., 20 lines max)
- Need up/down arrow navigation for scrolling through content
- Building a Component that implements the TUI Component interface
- Working with Clanker Ops or similar task boards that grow beyond viewport

## Procedure

1. **Create the ScrollableBoard class implementing Component interface:**
   ```typescript
   import type { Component, TUI } from "@mariozechner/pi-tui";
   
   export class ScrollableBoard implements Component {
     private scrollOffset = 0;
     private maxVisibleLines = 20;
     
     render(width: number): string[] {
       // Render only visible subset based on scrollOffset
       const lines = this.renderFullBoard(width);
       return lines.slice(this.scrollOffset, this.scrollOffset + this.maxVisibleLines);
     }
     
     handleInput(key: string, tui: TUI): void {
       if (key === 'up' && this.scrollOffset > 0) {
         this.scrollOffset--;
         tui.rerender();
       } else if (key === 'down') {
         this.scrollOffset++;
         tui.rerender();
       }
     }
   }
   ```

2. **Add scroll position indicator:**
   - Show "n/total" at bottom or use scrollbar visualization
   - Calculate total lines needed for all items

3. **Integrate with UI context:**
   - Use `ctx.hasUI` check before launching overlay
   - Hook into `/clanker overlay` command

4. **Connect to state:**
   - Use `getState()` to pull live task data
   - Apply selectors for filtering/grouped views

## Pitfalls

- **Import paths**: TypeScript ESM requires `.js` extensions in imports even for `.ts` files
- **TUI integration**: The `ui.custom()` method needs further exploration for full keyboard handling
- **Widget vs TUI**: Distinguish between persistent `setWidget` (for always-visible overlays) and `ui.custom()` (for interactive overlays)
- **Height constraints**: The TUI Component `render(width)` only receives width, not height - must manage height internally

## Verification

- Run node -e to check bracket/brace balance
- Verify no import errors with tsx or node --loader ts-node/esm
- Test scroll offset boundaries (can't scroll past start or end)
- Confirm up/down keys trigger rerender