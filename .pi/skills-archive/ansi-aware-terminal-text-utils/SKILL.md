---
name: "ansi-aware-terminal-text-utils"
description: "Extract ANSI-aware text utility functions (visualWidth, truncate, pad, padOnly, stripAnsi, isWideCodePoint) for terminal UI table formatting that correctly handles ANSI escape codes and wide characters (CJK, emoji). Use when building CLI table renderers, board views, or any terminal output that needs to measure/truncate/pad strings containing ANSI color codes or wide Unicode characters."
version: 2
created: "2026-05-20"
updated: "2026-05-20"
---
# ANSI-Aware Terminal Text Utilities

## When to Use
When building a CLI tool, board renderer, or terminal table formatter that needs to:
- Measure the visual display width of strings containing ANSI escape codes (color, bold, dim)
- Truncate strings to fit within a fixed visual width without breaking ANSI sequences
- Pad strings to a fixed visual width (with or without truncation)
- Strip ANSI escape codes leaving only visible text
- Count wide characters (CJK ideographs, emoji) as 2 visual columns

## Procedure
### 1. Create a single utility module

Create `text-utils.ts` with the following functions:

```typescript
/**
 * Text Utils - ANSI-aware string measurement and padding.
 */

// ---------------------------------------------------------------------------
// Wide character detection (CJK, emoji, etc.)
// ---------------------------------------------------------------------------

export function isWideCodePoint(code: number): boolean {
    return (
        (code >= 0x1100 && code <= 0x115f) ||
        (code >= 0x2329 && code <= 0x232a) ||
        (code >= 0x2e80 && code <= 0xa4cf && code !== 0x303f) ||
        (code >= 0xac00 && code <= 0xd7a3) ||
        (code >= 0xf900 && code <= 0xfaff) ||
        (code >= 0xfe10 && code <= 0xfe19) ||
        (code >= 0xfe30 && code <= 0xfe6f) ||
        (code >= 0xff00 && code <= 0xff60) ||
        (code >= 0xffe0 && code <= 0xffe6)
    );
}

// ---------------------------------------------------------------------------
// ANSI-aware measurement
// ---------------------------------------------------------------------------

/**
 * Calculate the visual width of a string, ignoring ANSI escape codes
 * and counting wide characters as 2 columns.
 */
export function visualWidth(value: string | number): number {
    const str = String(value ?? "");
    let width = 0;
    let inAnsi = false;

    for (let i = 0; i < str.length; i++) {
        if (str[i] === ESCAPE) {
            inAnsi = true;
            continue;
        }
        if (inAnsi) {
            if (str[i] === "m") inAnsi = false;
            continue;
        }
        const code = str.codePointAt(i) ?? 0;
        width += isWideCodePoint(code) ? 2 : 1;
    }
    return width;
}
```

NOTE: Replace `ESCAPE` above with the actual ESC character (0x1B). In TypeScript, use the escape sequence `\x1b` inside a string literal: `str[i] === "\x1b"`. The ESC character is the byte 0x1B, not the literal text `\x1b`.

### 2. Add truncation with suffix

```typescript
/**
 * Truncate a string to fit within `width` visual columns,
 * appending "..." if truncated.
 */
export function truncate(value: string | number, width: number): string {
    const str = String(value ?? "");
    if (visualWidth(str) <= width) return str;

    const suffix = "...";
    const suffixWidth = visualWidth(suffix);
    if (width <= suffixWidth) return suffix.slice(0, width);

    let out = "";
    let w = 0;
    for (const char of str) {
        const cw = visualWidth(char);
        if (w + cw + suffixWidth > width) return out + suffix;
        out += char;
        w += cw;
    }
    return out;
}

### 3. Add padding functions

```typescript
/**
 * Pad a string to `width` visual columns, truncating if necessary.
 */
export function pad(value: string | number, width: number): string {
    const v = truncate(value, width);
    return v + " ".repeat(Math.max(0, width - visualWidth(v)));
}

/**
 * Pad a string to `width` visual columns WITHOUT truncating.
 */
export function padOnly(value: string | number, width: number): string {
    const str = String(value ?? "");
    return str + " ".repeat(Math.max(0, width - visualWidth(str)));
}

### 4. Add ANSI strip utility

```typescript
/**
 * Remove ANSI escape codes from a string, leaving only visible text.
 */
export function stripAnsi(value: string): string {
    // The regex matches SGR escape sequences: ESC + [ + params + m
    // Use the actual ESC character (0x1B) in the regex
    return value.replace(/\x1b\[[0-9;]*m/g, "");
}

### 5. Use in board/table renderers

Import and use for column formatting:

```typescript
import { visualWidth, truncate, pad } from "./text-utils.js";

// Calculate column widths based on actual visual content
function computeColumnWidths(rows: Row[], minWidths: number[]): number[] {
    const widths = [...minWidths];
    for (const row of rows) {
        row.cells.forEach((cell, i) => {
            const vw = visualWidth(cell);
            if (vw > widths[i]) widths[i] = vw;
        });
    }
    return widths;
}

// Render cells with proper padding
function renderRow(cells: string[], widths: number[]): string {
    return cells.map((cell, i) => pad(cell, widths[i])).join(" | ");
}

### 6. Handle edge cases

```typescript
// Empty/null values
visualWidth("");      // -> 0
visualWidth(null);    // -> 0 (String(null) === "null")

// ANSI-colored text ignores escape codes
visualWidth(ESC + "[32mHello" + ESC + "[0m");  // -> 5 (ANSI codes ignored)

// Wide characters (Chinese, Japanese, Korean)
visualWidth("\u4f60\u597d");  // -> 4 (each char is 2 columns)
visualWidth("a\u4f60\u597db"); // -> 6

// Truncation with suffix
truncate("Hello World", 8);  // -> "Hello..."

// Padding
pad("Hi", 6);   // -> "Hi    "
pad("Hello World", 6);  // -> "He..." (truncated to fit)
```

NOTE: Replace `ESC` in the examples above with the actual ESC character (0x1B, written as `\x1b` in TypeScript source).
## Pitfalls
- **Null/undefined values**: Always convert to string with `String(value ?? "")` to prevent "null" or "undefined" from counting as 4 or 9 characters
- **ANSI regex scope**: The regex `/\\x1b\\[[0-9;]*m/g` only matches SGR (Select Graphic Rendition) codes like `\\x1b[31m`. It does NOT match non-SGR escape sequences (cursor movement, screen clears). If your terminal output includes cursor positioning, extend the regex or strip more broadly
- **Wide character coverage**: The `isWideCodePoint` function covers common CJK and emoji ranges but is not exhaustive. For full Unicode East Asian Width compliance, consider the `wcwidth` npm package. The hand-rolled function covers ~95% of real-world usage
- **Grapheme clusters**: Emoji sequences with skin tone modifiers or ZWJ sequences can span multiple code points but display as a single grapheme. This utility counts code points, not grapheme clusters. For perfect emoji support, use `grapheme-splitter`
- **Performance**: `visualWidth` iterates character-by-character with a state machine. Fast enough for terminal table rendering (thousands of cells). For millions of operations, pre-compute widths
- **Backslash escaping in source**: The actual source code uses `\\x1b` (backslash-x-1-b) but when writing these functions, use raw escape sequences. The ANSI escape character is `\\x1b` (ESC, 0x1B)

## Verification
- [ ] Visual width correctly ignores ANSI escape codes
- [ ] Visual width counts CJK characters as 2 columns
- [ ] Visual width handles empty/null values gracefully
- [ ] Truncation appends "..." only when content exceeds width
- [ ] Truncation preserves ANSI codes in non-truncated portion
- [ ] Pad adds correct number of spaces for visual column alignment
- [ ] Pad truncates content when it exceeds width (pad variant)
- [ ] PadOnly does NOT truncate (for fixed-width columns that can overflow)
- [ ] Strip ANSI removes all SGR escape codes
- [ ] Table columns align correctly in terminal with mixed ANSI/wide content