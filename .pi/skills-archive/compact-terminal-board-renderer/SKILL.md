---
name: "compact-terminal-board-renderer"
description: "Render a compact, borderless terminal board using indentation and status symbols instead of ANSI box-drawing. Use when your CLI tool renders a multi-section task/work board and needs a narrow-width mode for small terminals or users who prefer minimal output."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

- Your CLI tool renders a board, table, or multi-section work queue in a terminal
- Users need a compact/narrow-width rendering mode (e.g., `/clanker compact` subcommand)
- You want to avoid ANSI box-drawing characters for cleaner output
- The board has multiple sections (active, queued, done, failed) with status symbols

Do **not** use for:
- Full-width bordered tables that need column alignment
- Data-grid rendering (use bordered table renderers instead)
- HTML/CSS-based rendering (only terminal ANSI)

## Procedure

### 1. Define status symbol map

Map each task/section state to a single Unicode character:

| State | Symbol | Meaning |
|-------|--------|---------|
| Active/in-progress | ◐ | Work in progress |
| Queued/pending | ○ | Not yet started |
| Special/highlighted | ⊘ | Crossed-out circle for assigned tasks |
| Failed/errored | ✗ | Failed execution |
| Done/completed | ✓ | Successfully completed |
| Important | ! | Needs attention / don't forget |
| Dispatched | ⇢ | In flight / dispatched |

### 2. Build summary header

Render a single-line header showing section counts separated by `·`:

```
Clanker Ops  3 active · 1 failed · 5 queued · 2 done
```

Skip any section with zero items. Only show `failed` count when > 0.

### 3. Render sections with indentation

For each section (active, failed, reminders, queued, done), render:
- A **blank line** before the section header
- A **section header** in plain text (no ANSI decoration), e.g., `Active:`
- Each item on one line with: `  <symbol> #<id> <title>[ <metadata>]`

For the metadata portion:
- Active form (present-continuous label) in `()` — e.g., `(writing tests)`
- Owner with `@` prefix — e.g., `@dad_웃`
- Last-run timestamp using the `relative-time-formatter` skill

### 4. Handle list overflow

When a section contains more than 10 items, show only the first 10 and append:

```
  ... 7 more
```

Use `slice(0, 10)` on the array and compute remaining via `array.length - 10`.

### 5. Color owner names

Apply owner-specific ANSI color, but only to the owner text itself (not padding):
- Use `graf` function: paint the owner text, then pad with uncolored spaces
- Common owner colors: dad (dark blue bg / light blue text), tom (green bg / dark green), other 웃 users (cyan text), default (gray)

### 6. Done summary

For the done section, render only a single-line count (no individual items):

```
✓ 12 done
```

### 7. Implementation checklist

```typescript
interface CompactRendererOptions {
  tasks: readonly Task[];
  width?: number;
  filter?: Task[];
}

export function renderCompact(tasks: readonly Task[], options: CompactRendererOptions): string {
  const present = presentBoard(tasks);  // group tasks into sections
  const { groups } = present;
  const lines: string[] = [];

  // 1. Header summary
  const parts: string[] = [];
  if (groups.active.length) parts.push(`${groups.active.length} active`);
  // ... failed, queued, done

  // 2. Active section
  if (groups.active.length) {
    lines.push('', 'Active:');
    for (const item of groups.active) {
      lines.push(`  ◐ #${item.id} ${item.title}${metadata}`);
    }
  }

  // 3. Failed section
  // 4. Reminders section  
  // 5. Queued section (first 10 + overflow)
  // 6. Done count
  return lines.join('\n');
}
```

## Pitfalls

- **Symbol width mismatch**: Unicode symbols (◐ ○ ⊘ ✗) may display at different widths in different terminals. Test in both wide and narrow terminals. Use a visual-width calculation function (e.g., `visualWidth(str)`) rather than `.length` for alignment.
- **Color on non-owner text**: Do NOT color whitespace/padding around owner names — only the owner name string itself. Apply color via a span function that paints only the text portion: `paint(text) + ' '.repeat(padding)`.
- **Empty state**: If all tasks/sections are empty, render just the header with `0` counts or a minimal message. Never crash on empty arrays.
- **Overflow edge**: Section with exactly 10 items — do NOT show `... N more`. Only show it when length > 10 (i.e., `>= 11`).
- **Symbol meaning**: Add a glyph legend in the board footer for accessible/semantic understanding of symbols.
- **Don't mix rendering styles**: The compact mode should use ZERO box-drawing characters (│ ─ ┤ ╰). If any appear, the mode is not truly compact — switch to plain indentation.

## Verification

1. Empty task list renders a minimal header with 0/empty counts — no crash
2. Single task in active section shows `◐ #id title` with correct indentation
3. >10 tasks in queued section shows first 10 plus `... N more` where N = total - 10
4. Exactly 10 tasks does NOT show overflow line
5. No ANSI box-drawing characters (│ ─ ├ ┤ ╰ ╭ ╮ ╯ ╰) appear in output
6. Owner name is colored but trailing whitespace is gray
7. Re-rendering after task status change shows updated symbols and counts
8. Summary header uses `·` as separator (U+00B7 middle dot), never `|` or `,`