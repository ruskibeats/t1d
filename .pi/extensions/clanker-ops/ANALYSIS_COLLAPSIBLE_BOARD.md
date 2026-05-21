# Clanker Board Collapsible/Scrollable Analysis

## Current State

### Widget Implementation (`todo-overlay.ts`)
- Uses `setWidget` with factory-form registration
- Placement: `aboveEditor` (fixed position)
- Renders via `renderClankerBoard()` returning `string[]`
- No height constraint awareness - renders ALL tasks

### Board Renderer (`view/board.ts`)
- **Full board**: 107 tasks → ~40 lines for completed + active + queued sections
- **Compact board**: Already exists, truncates queued at 10 items
- Both modes render ALL sections without height limits
- No scrolling mechanism - just dumps all lines

### Layout Selector (`state/selectors.ts`)
- `selectOverlayLayout()` already implements **12-line collapse logic**
- Drops completed first, truncates non-completed tail
- Returns `{ visible, hiddenCompleted, truncatedTail }`
- **Currently unused** in the widget render path!

---

## Possibility 1: Height-Constrained Widget (Recommended)

### Concept
Use `selectOverlayLayout()` in the widget to respect terminal height.

### Current Code Path
```typescript
// todo-overlay.ts:renderWidget()
private renderWidget(theme: Theme, width: number): string[] {
    // Currently renders ALL tasks
    return renderClankerBoard(getState().tasks, { width }).split("\n");
    // Returns ~40+ lines
}
```

### Implementation
```typescript
private renderWidget(theme: Theme, width: number, height?: number): string[] {
    const tasks = getState().tasks;
    
    // Determine budget based on available height
    const budget = height ? height - 1 : 12; // Reserve 1 for heading
    
    // Apply overlay layout
    const { visible, hiddenCompleted, truncatedTail } = selectOverlayLayout(
        getState(), 
        Math.max(3, budget)
    );
    
    // Render with filtered tasks
    const lines = renderClankerBoard(visible, { width });
    
    // Append overflow summary if any
    if (hiddenCompleted > 0 || truncatedTail > 0) {
        lines.push(`... (${hiddenCompleted} done, ${truncatedTail} more)`);
    }
    
    return lines;
}
```

### Pros
- Uses existing `selectOverlayLayout()` logic
- Drop-in change to widget
- Maintains backward compatibility
- Follows documented pattern in selectors.ts comments

### Cons
- Requires access to `height` in widget render
- `renderClankerBoard` currently ignores height
- May need to modify `RenderBoardOptions`

---

## Possibility 2: Scrollable Overlay Widget

### Concept
Replace `aboveEditor` widget with a scrollable overlay that the user can navigate.

### Implementation Path
```typescript
// Use overlay instead of widget for true scrolling
import { type TUI } from "@mariozechner/pi-tui";

this.tui?.showOverlay(
    scrollableBoardComponent,
    { maxHeight: "60%", width: "100%" }
);
```

### Required Changes
1. Create `ScrollableBoard` Component implementing `TUI.Component`
   - `render(width)` - returns visible slice of lines
   - `handleInput()` - respond to up/down arrow keys
   - `scrollOffset: number` - track current scroll position

2. TUI supports overlays via `showOverlay(component, options)`
   - `maxHeight` can be percentage or absolute
   - Focus management built-in
   - `OverlayHandle` for show/hide control

### Pros
- True scrolling with keyboard navigation
- User can see all tasks without terminal resize
- Modern TUI interaction pattern

### Cons
- More complex implementation
- Requires `TUI` access (already injected in render factory)
- Need to handle focus/unfocus lifecycle
- May conflict with editor focus

---

## Possibility 3: Section Collapse Toggle

### Concept
Add collapse/expand controls for each board section (Active, Don't Forget, Queued, Done).

### Implementation Approaches
1. **ANSI button simulation**: `[↓ Active]` vs `[↑ Active]` 
   - Click detection via mouse reporting (if enabled)
   - Or keyboard shortcuts when overlay has focus

2. **Per-section height limits**: 
   ```typescript
   const SECTION_LIMITS = {
     active: 5,
     queued: 8,
     done: 0, // hide by default
   };
   ```

3. **State tracking**: Add `collapsedSections: Set<string>` to widget state
   - Persist per-session
   - Keyboard toggle: `c` to collapse all, `x` to expand all

### Example UI
```
Clanker Ops  0 active · 40 queued · 64 done
╭─── Clanker Ops ───╮
│ Active: (none)                · collapsed: done (64)
│ Queued: ○ #1 [item]           · use /clanker all to expand
│         ○ #2 [item]
├───────────────────┤
│ ▼ Done (64)                   ▼/► expand with /clanker done
╰───────────────────╯
```

### Pros
- User control over visibility
- Progressive disclosure
- Matches IDE panel patterns

### Cons
- More UI state to manage
- No click handling without mouse support
- Keyboard shortcuts need TUI focus

---

## Possibility 4: Compact Widget Mode (Already Exists)

### Current State
- `/clanker compact` renders `renderClankerBoardCompact()`
- Truncates queued at 10 items
- No borders, cleaner output

### Enhancement Opportunity
Apply compact logic to widget mode:
```typescript
// In todo-overlay.ts
private renderWidget(theme: Theme, width: number): string[] {
    const tasks = getState().tasks;
    // Use compact renderer for widget
    return renderClankerBoardCompact(tasks, { width });
}
```

### Pros
- Minimal change
- Alread exists and works
- Designed for narrow terminals

### Cons
- Loses full board information
- No collapse, just truncation

---

## Possibility 5: Virtual Scrolling with Height Awareness

### Concept
Render only the lines that fit in the available space, with virtual scroll position.

### Based On
- `overlay-layout-calculation` skill (already in memory)
- Existing `selectOverlayLayout` function

### Implementation
```typescript
interface ScrollableBoardState {
    scrollTop: number;
    viewportHeight: number;
    collapsedSections: Set<string>;
}

function renderScrollableBoard(
    tasks: Task[], 
    options: { width: number; height: number; scrollTop?: number }
): string[] {
    // 1. Group tasks by section
    const board = presentBoard(tasks);
    
    // 2. Calculate line heights per section
    const sectionHeights = {
        header: 3,
        legend: 2,
        active: board.groups.active.length * 1,
        dontForget: board.groups.dontForget.length * 1,
        queued: board.groups.queued.length * 1,
        done: 1, // summary line only
    };
    
    // 3. Slice visible range based on scrollTop
    // 4. Add scroll indicators ▲▼ at top/bottom when not at extremes
}
```

### Pros
- Memory efficient for large task lists
- Smooth scrolling experience
- Familiar paradigm from IDEs

### Cons
- Complex line-to-section mapping
- Need scroll position state
- Arrow key handling logic

---

## Technical Constraints & Considerations

### Terminal/TUI Capabilities
From `pi-tui/dist/tui.d.ts`:
- `Component.render(width: number): string[]` - height not passed
- `OverlayOptions.maxHeight?: SizeValue` - can limit overlay height
- `TUI.showOverlay(component, options)` - creates scrollable overlay
- Components can implement `handleInput(data: string)` for keyboard

### Widget Limitations
From `extensions/types.d.ts`:
```typescript
setWidget(key: string, content: string[] | undefined | ((tui, theme) => Component)): void
```
- Widget renders `string[]` - no built-in scrolling
- `aboveEditor` placement puts it in a fixed container
- `render(width)` doesn't receive height

### Height Detection Options
1. **Process environment**: `process.stdout.rows` (dynamic)
2. **TUI injection**: TUI knows terminal size internally
3. **Hard-code**: Use reasonable default (12-20 lines)

---

## Recommendation

### Short Term (MVP)
1. **Apply `selectOverlayLayout` to widget** - uses existing logic
2. **Hard-code height budget** to 12-15 lines initially
3. **Show overflow summary** ("... 64 done, 3 more")

### Medium Term (Enhanced)
1. **Overlay-based scrollable board** - use TUI overlay
2. **Keyboard navigation** - up/down arrows scroll sections  
3. **Section collapse** - `c` to collapse/expand sections

### Long Term (Polish)
1. **Height-aware rendering** - detect terminal height
2. **Mouse scroll support** - wheel events to TUI
3. **Persistent collapse state** - remember per-session

---

## Key Files to Modify

| File | Change |
|------|--------|
| `todo-overlay.ts` | Apply `selectOverlayLayout`, add height awareness |
| `view/board.ts` | Add height parameter to `renderClankerBoard` |
| `view/board-model.ts` | Add height-based truncation mode |
| `state/selectors.ts` | `selectOverlayLayout` already exists - use it! |
| `commands/router.ts` | Option to force compact/expanded mode |

---

## Testing Considerations

1. **Empty state**: Widget should hide when no tasks
2. **Small terminals**: Board should fit 15-line minimum
3. **Large task lists**: 50+ tasks should show reasonable subset
4. **Dynamic updates**: Adding/removing tasks should re-render appropriately
5. **Done section**: Should be collapsed by default in widget

---

## Related Skills Available

- `overlay-layout-calculation` - Priority-based item selection for limited space
- `compact-terminal-board-renderer` - Minimal borderless rendering
- `relative-time-formatter` - Time formatting for "last ran" column