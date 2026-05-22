---
name: "overlay-layout-calculation"
description: "Calculate which items to display in a constrained terminal overlay widget by prioritizing visible items, dropping completed first, and handling overflow with summary counts. Use when building CLI widgets with limited vertical space that need intelligent item prioritization."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

- Building a CLI overlay/widget with limited vertical space (e.g., 10-20 lines)
- Need to show "top N items" from a larger dataset intelligently
- Want to handle overflow gracefully with summary counts (e.g., "and 5 more")
- Need to prioritize certain items (show active before completed)

## Procedure

### 1. Define the Layout Interface

```typescript
export interface OverlayLayout<T> {
  visible: readonly T[];
  hiddenCompleted: number;  // Completed items dropped
  truncatedTail: number;    // Non-completed items truncated
}
```

### 2. Implement Priority-Ordered Selection

```typescript
export function selectOverlayLayout<T extends { status: string }>(
  all: readonly T[],
  budget: number,  // Available line count
  priorityOrder: string[] = ["active", "in_progress", "pending"],  // Show these first
  completedStatus: string = "completed",  // Status to drop first
): OverlayLayout<T> {
  // Early exit - everything fits
  if (all.length <= budget) {
    return { visible: all, hiddenCompleted: 0, truncatedTail: 0 };
  }

  const innerBudget = budget - 1;  // Reserve 1 slot for summary row

  // Separate by priority
  const nonCompleted = all.filter((t) => t.status !== completedStatus);
  const completed = all.filter((t) => t.status === completedStatus);
  const totalCompleted = completed.length;

  // All non-completed fit - show them + some completed
  if (nonCompleted.length <= innerBudget) {
    const kept = new Set<T>(nonCompleted);
    for (const t of completed) {
      if (kept.size >= innerBudget) break;
      kept.add(t);
    }
    const visible = [...kept];
    const shownCompleted = visible.filter((t) => t.status === completedStatus).length;
    return {
      visible,
      hiddenCompleted: totalCompleted - shownCompleted,
      truncatedTail: 0,
    };
  }

  // Non-completed overflow - show first N, drop all completed
  const visible = nonCompleted.slice(0, innerBudget);
  const truncatedTail = nonCompleted.length - innerBudget;
  return { visible, hiddenCompleted: totalCompleted, truncatedTail };
}
```

### 3. Apply to Terminal Widget

```typescript
function renderWidget(tasks: Task[], rows: number): string[] {
  const { visible, hiddenCompleted, truncatedTail } = selectOverlayLayout(tasks, rows);
  
  const lines: string[] = [];
  for (const task of visible) {
    lines.push(formatTaskLine(task));
  }
  
  // Summary line
  if (hiddenCompleted > 0) {
    lines.push(`(${hiddenCompleted} done)`);
  } else if (truncatedTail > 0) {
    lines.push(`... ${truncatedTail} more`);
  }
  
  return lines;
}
```

## Pitfalls

1. **Always reserve space for summary** - Subtract 1 from budget to avoid overflow when showing the "X more" line
2. **Deep copy selections** - Use `.filter()` not `.slice()` on state arrays if you'll mutate later
3. **Status string comparison** - Use `===` for status comparisons, not fuzzy matching
4. **Empty state handling** - Return empty arrays, not undefined/null for visible items
5. **Priority order matters** - Put most important statuses first in the priority array

## Verification

- [ ] Empty input returns `{ visible: [], hiddenCompleted: 0, truncatedTail: 0 }`
- [ ] All items fit returns all items in visible, no overflow
- [ ] Non-completed overflow shows first N by insertion order
- [ ] Completed items are hidden first when total > budget
- [ ] Summary line count matches hidden items accurately
- [ ] Truncation never splits a displayed item in half (always whole items)