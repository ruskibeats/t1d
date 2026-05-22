---
name: "remove-ts-nocheck-from-legacy"
description: "Remove @ts-nocheck from a legacy TypeScript file: analyze types, extract helpers into focused modules, add proper type annotations, remove the suppression, and verify no regressions."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Remove `@ts-nocheck` from Legacy TypeScript Files

## When to Use

Remove `// @ts-nocheck` from a legacy TypeScript file that has grown large and has accumulated this suppression at the top. Use when:

- A file has `@ts-nocheck` suppressing all type errors
- The file mixes rendering, business logic, and file I/O
- You need to add types before making further changes
- The file is large (300+ lines) with multiple concerns

Do NOT use for:
- Small files (under 100 lines) — just add types inline
- Files where the module boundary is unclear — analyze first, then decide
- Generated files or files owned by an external tool

## Procedure

### Step 1 — Scan the full file and identify concerns

Read the entire file. Categorize every export/function into domains:

- **Rendering** — ANSI formatting, string output, display logic
- **Business logic** — classification, validation, sorting, deduplication
- **Text utilities** — measurement, padding, truncation (ANSI-aware)
- **File I/O** — reading/writing state files, plan files
- **Type definitions** — inline types, interfaces, enums

### Step 2 — Create the type definitions module if missing

If the file uses ad-hoc or `any` types, first create a proper `types.ts` (or extend an existing one) with:

```typescript
// tool/types.ts
export interface Task {
  id: number;
  item: string;
  status: TaskStatus;
  tags?: string[];
  assigned?: string;
  blockedBy?: number[];
  createdAt: string;
  updatedAt: string;
}

export type TaskStatus =
  | "pending" | "in_progress" | "completed"
  | "deleted" | "failed" | "cancelled" | "deferred";
```

**Pitfall**: Don't over-engineer types in the first pass. Create exactly what the file needs — you can refine later.

### Step 3 — Extract pure utility functions first

Create a helper module (e.g., `text-utils.ts`) for pure functions that have no side effects and no file I/O:

- ANSI-aware `visualWidth()`, `truncate()`, `pad()`, `stripAnsi()`
- Wide-character detection (CJK, emoji, etc.)
- Any string formatting with no external dependencies

```typescript
// text-utils.ts — pure, no side effects, fully testable
export function visualWidth(value: string): number {
  let width = 0, inAnsi = false;
  for (let i = 0; i < value.length; i++) {
    if (value[i] === "\x1b") { inAnsi = true; continue; }
    if (inAnsi) { if (value[i] === "m") inAnsi = false; continue; }
    width += isWideCodePoint(value.codePointAt(i) ?? 0) ? 2 : 1;
  }
  return width;
}
```

Key markers of "extractable to pure module":
- No `import` of state or file modules
- No `process.cwd()`, `fs`, `readFileSync`, `writeFileSync`
- Pure input → output transformation

### Step 4 — Extract business logic into a model module

Create a model module (e.g., `board-model.ts`) for all classification, sorting, grouping, and deduplication logic:

```typescript
// board-model.ts — pure business logic, no rendering, no file I/O
import { visualWidth } from "./text-utils.js";
import type { Task } from "../tool/types.js";

export function isDontForget(task: Task): boolean { /* ... */ }
export function isDuplicate(task: Task, all: Task[]): boolean { /* ... */ }
export function rankTask(task: Task): number { /* ... */ }
```

**Pitfall**: Be careful with optional chaining (`?.`) on arrays. `groups.active?.length` treats the group as possibly undefined, requiring all consumers to check. Use `groups.active.length` if the array always exists (even if empty), or initialize groups as `{ active: [], completed: [], ... }`.

### Step 5 — Rewrite the main file with type annotations

Now rewrite the original file:
1. Remove `// @ts-nocheck`
2. Add proper type annotations to all function signatures
3. Import from the extracted modules instead of defining inline
4. Remove file I/O — accept data as parameters (`Task[]` instead of reading from disk)
5. Remove dead exports that were never called

```typescript
// board.ts — now typesafe, no @ts-nocheck
import type { Task } from "../tool/types.js";
import { presentBoard, computeColumnWidths } from "./board-model.js";
import { pad, padOnly } from "./text-utils.js";

export function renderBoard(tasks: Task[], options?: RenderOptions): string {
  // Pure rendering — all data is passed in
}
```

### Step 6 — Update all callers

Find every file that imports from the original module and update:
- If you removed file I/O, callers must now pass data (from their own state/context)
- If you renamed exports, update import names
- If you removed dead exports, remove import references

**Pitfall**: Use `grep -r "import.*from.*board" --include="*.ts"` to find all callers before making changes.

### Step 7 — Verify no regressions

```bash
# Type-check the entire project
npx tsc --noEmit

# Run existing tests
npm test

# Test the specific feature (e.g., render the board)
# Manually verify the output looks correct
```

## Pitfalls

- **`.?` on arrays causes downstream null checks**: If you write `groups.active?.length`, TypeScript types `groups.active` as possibly undefined. Every consumer must then check. Initialize your group maps with all keys and empty arrays: `{ active: [], completed: [], failed: [], blocked: [], dontForget: [], queued: [] }`.
- **Missing imports after extraction**: After moving functions, grep for all callers. The TypeScript compiler will catch some, but dynamic paths or re-exports might not.
- **Dead exports**: Files with `@ts-nocheck` often accumulate unused exports. Before extracting a function, grep for its callers. If none, drop it.
- **ANSI codes in width measurement**: When calculating column widths, you must strip ANSI codes before measuring. `string.length` counts escape sequences as characters. Always use `visualWidth()`.
- **Regressions in terminal output**: After refactoring, run the actual terminal command and visually verify the output. Column alignment, color, and truncation are easy to miss in unit tests.

## Verification

```bash
# TypeScript compilation must pass
npx tsc --noEmit

# Existing tests must pass
npm test

# The original file no longer contains @ts-nocheck
grep -rn "@ts-nocheck" path/to/your/file.ts || echo "No @ts-nocheck found — success"

# All functions have explicit return types
grep -n "): " path/to/your/file.ts  # Should see typed returns everywhere