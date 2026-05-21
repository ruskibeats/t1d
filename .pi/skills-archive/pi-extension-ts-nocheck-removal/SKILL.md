---
name: "pi-extension-ts-nocheck-removal"
description: "Remove @ts-nocheck from Pi extension files by extracting business logic into typed, testable modules, then rewriting the original file with proper TypeScript types. Use when fixing type-checking bypass files in Pi extensions during refactoring or architecture deepening."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Pi Extension @ts-nocheck Removal

## When to Use
When an existing Pi extension file uses `// @ts-nocheck` and you need to restore proper TypeScript checking during refactoring/architecture deepening. This procedure eliminates the suppression and makes the file type-safe.

## Procedure

### 1. Identify the suppression scope
```bash
grep -rn '@ts-nocheck' . --include='*.ts' | grep -v node_modules
```
Check all callers of the target file's exports. Every caller must be updated.

### 2. Extract business logic into typed modules
Create focused, testable modules in appropriate subdirectories:
- Pure functions (no I/O) → typed module with explicit parameters
- File/system I/O → Repository pattern (interface + implementations)
- String formatting → utility module with exported helpers

**Key rule**: The new modules must have ZERO `// @ts-nocheck` and ZERO `any`. Fix every type error.

### 3. Update data types/temp
```typescript
// Before (in @ts-nocheck file):
const ansi = { red: (v) => `\x1b[1;91m${v}\x1b[0m` };

// After (typed module):
interface AnsiColors {
  red: (v: string) => string;
  green: (v: string) => string;
}
const ansi: AnsiColors = {
  red: (v: string) => `\x1b[1;91m${v}\x1b[0m`,
};
```

### 4. Rewrite the original file without @ts-nocheck
- Remove the `// @ts-nocheck` directive
- Import from the new typed modules
- Accept data as parameters (no inline `readFileSync`, no `process.cwd()`)
- Export clean function signatures with explicit types

### 5. Update all callers
```bash
grep -rn "renderClankerBoard" . --include='*.ts' | grep -v node_modules
```
For each caller:
- Update imports to match new file exports
- Pass required data as arguments instead of relying on side-effect reads
- Fix any type mismatches

### 6. Verify zero @ts-nocheck remain
```bash
grep -rn '@ts-nocheck' .pi/extensions/YOUR-EXTENSION/ --include='*.ts'
```
Expect zero results.

### 7. Test compilation
```bash
cd /root/t1d && npx tsc --noEmit --pretty 2>&1 | head -30
```

### 8. Commit
```bash
git add -A && git commit -m "clanker-ops: fix FILENAME.ts — remove @ts-nocheck, extract logic, add types"
```

## Real Example (board.ts → board-model.ts + text-utils.ts)

**Before:**
- `view/board.ts` (401 lines, `// @ts-nocheck`, 3 concerns mixed)
- Embedded `readFileSync` file I/O
- Inline ANSI text measurement
- Business logic, grouping, rendering all mixed

**After:**
- `view/text-utils.ts` (~100 lines) — ANSI-aware string width, padding, truncation
- `view/board-model.ts` (~350 lines) — Task classification, grouping, column width computation, view model creation
- `view/board.ts` (~220 lines, no @ts-nocheck) — Pure ANSI rendering, accepts `Task[]` as parameter
- All callers updated: `commands/router.ts`, `todo-overlay.ts`

## Pitfalls

1. **Don't split too thin** — One extracted module per concern is ideal. Over-splitting creates import spaghetti.
2. **Update ALL callers simultaneously** — Partial updates leave compilation broken. Fix every caller in one pass.
3. **Don't mix I/O in renderers** — Render functions must accept data as parameters. File reads belong in the caller.
4. **Naming collision on old exports** — When renaming exports (e.g. `renderClankerBoard` → `renderBoard`), update every import site. Consider re-exporting old names temporarily.
5. **`type BoardViewModel` used before defined** — When extracting types into a new module, ensure import ordering doesn't create circular dependencies.

## Verification

1. ✅ `grep -rn '@ts-nocheck' extension-dir/ --include='*.ts'` returns zero
2. ✅ `npx tsc --noEmit --pretty` compiles without errors
3. ✅ All callers (router, overlay, index) import from correct paths
4. ✅ No `any` types in extracted modules
5. ✅ Board renders identically in `/clanker` command and overlay