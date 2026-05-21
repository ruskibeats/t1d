---
name: "extract-command-router"
description: "Extract monolithic command routing and handler logic from a CLI handler file into a dedicated router module with a unified context type, handler map, and natural-language intercept fallback. Use when a Pi extension or CLI tool has a single file mixing tool registration, command routing, and multiple handlers."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

- A CLI tool or Pi extension has a single file (e.g., `todo.ts`) that mixes tool/command registration with routing logic and multiple command handlers
- The handler file is 300+ lines with nested `if`/`switch` statements for subcommand dispatch
- You need to unit-test individual handlers without triggering full tool registration
- Multiple command handlers open files, read state, or format output inline — making the file hard to reason about
- You have a `/command` with subcommands like `help`, `eod`, `dispatch`, `focus` and natural-language fallback (intercept)

## Procedure

### 1. Identify what to extract

A monolithic command handler typically mixes three concerns:

| Concern | What it does | Extract into |
|---------|-------------|-------------|
| **Routing logic** | Parses input, maps subcommand strings to handlers | `commands/router.ts` |
| **Handler implementations** | Logic for each subcommand (help, dispatch, focus, etc.) | Inline functions or separate `commands/*-handler.ts` files (see Decision) |
| **Registration/boilerplate** | `pi.registerCommand(...)`, `pi.registerTool(...)` | Stays in original file as thin facade |

### 2. Decide: inline handlers vs. separate files

**Inline all handlers in router.ts** when:
- Each handler is <60 lines
- The router file stays under ~250 lines
- Handlers share a lot of context/state imports

**One file per handler** (e.g., `commands/dispatch-handler.ts`) when:
- Any single handler is 100+ lines
- The router would exceed ~300 lines
- Different handlers have different dependencies (e.g., dispatch needs spawner, help needs no state)

### 3. Define the handler context type

Create a shared context interface that all handlers receive:

```typescript
// commands/router.ts or commands/types.ts
export interface CommandContext {
  input: string;          // Raw trimmed input
  subcommand: string;     // First token, lowercased
  notify: (msg: string, level: string) => void;  // Output channel
  hasUI: boolean;         // Whether interactive UI is available
}
```

**Key patterns**:
- `notify` abstracts the output mechanism (works with both `ctx.ui.notify()` and plain stdout)
- `hasUI` lets handlers branch on interactive vs. non-interactive mode
- Keep the context minimal — add fields only when multiple handlers need them

### 4. Build the handler map

```typescript
type Handler = (ctx: CommandContext) => Promise<boolean>;

const handlers: Record<string, Handler> = {
  help: handleHelp,
  "--help": handleHelp,
  "-h": handleHelp,
  eod: handleEod,
  dispatch: handleDispatch,
  focus: handleFocus,
};
```

**Pattern: aliases** — Map `"--help"` and `"-h"` alongside `"help"` so the router doesn't need to normalize aliases.

**Return value convention**: Return `true` if the board/UI should re-render after the handler completes (e.g., after creating a new task). Return `false` if no re-render needed.

### 5. Implement individual handlers

Each handler is a standalone async function. Keep them focused:

```typescript
/** No subcommand — show the board */
async function handleEmpty(ctx: CommandContext): Promise<boolean> {
  const board = renderBoard(getState().tasks, { width: 120, includeDone: true });
  ctx.notify(board, "info");
  return false;
}

/** Help text */
async function handleHelp(ctx: CommandContext): Promise<boolean> {
  ctx.notify(CLANKER_HELP_TEXT, "info");
  return false;
}
```

**Handler patterns**:
- **Read-only handlers** (`help`, `board`): Just `getState()` and `ctx.notify()`. Pure reads.
- **Mutating handlers** (`dispatch`): Use state mutation functions (`applyTaskMutation` + `commitState`), then notify.
- **Interact-only handlers** (`focus`): Branch on `ctx.hasUI` for interactive vs. non-interactive paths.
- **Natural-language intercept** (`handleIntercept`): The catch-all that creates new work items from unrecognized input.

### 6. Implement the main route function

```typescript
/**
 * Route a /command to its handler.
 * Handles: known subcommands, empty input (board), and natural-language fallback.
 */
export async function routeCommand(
  input: string,
  notify: (msg: string, level: string) => void,
  hasUI: boolean,
): Promise<void> {
  const subcommand = input.split(" ")[0].toLowerCase();
  const ctx: CommandContext = { input, subcommand, notify, hasUI };

  // Empty command — show board
  if (!input) {
    await handleEmpty(ctx);
    return;
  }

  // Known subcommand
  const handler = handlers[subcommand];
  if (handler) {
    await handler(ctx);
    return;
  }

  // Natural language interception — treat as new work item
  await handleIntercept(ctx);
}
```

**Key pattern: Intercept fallback** — Unknown input is treated as creating a new work item rather than showing an error. This makes the command feel conversational.

### 7. Refactor the original file into a thin facade

```typescript
// Original: todo.ts (before) — ~400 lines with everything inline
// After: todo.ts — ~50 lines, thin registration facade

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export function registerTodoTool(pi: ExtensionAPI): void {
  pi.registerTool({
    name: TOOL_NAME,
    parameters: TodoParamsSchema,
    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      // Tool logic stays here (it's separate from command routing)
      const result = applyTaskMutation(getState(), params.action, params as TaskMutationParams);
      commitState(result.state);
      return buildToolResult(params.action, params as TaskMutationParams, result.state, result.op);
    },
    // ...
  });
}

export function registerClankerCommand(pi: ExtensionAPI): void {
  pi.registerCommand(COMMAND_NAME, {
    description: "Clanker Ops — show the work board",
    handler: async (args, ctx) => {
      const input = typeof args === "string" ? args.trim() : "";
      const { routeCommand } = await import("./commands/router.js");
      await routeCommand(
        input,
        (msg, level) => ctx.ui.notify(msg, level as "info" | "error"),
        ctx.hasUI ?? false,
      );
    },
  });
}
```

**Key patterns**:
- Dynamic `import("./commands/router.js")` — avoids circular or eager loading at module scope
- Adapter from `ctx.ui.notify(msg, level)` to the simpler `(msg, level) => void` signature used by the router
- `ctx.hasUI ?? false` — provides a sensible default when the UI context is unavailable

### 8. Verify

```bash
# Compilation
npx tsc --noEmit --pretty 2>&1 | head -20

# Check all callers still work
grep -rn "registerClankerCommand\|routeCommand" . --include="*.ts" | grep -v node_modules

# Verify handlers are reachable
grep -n "const handlers:" commands/router.ts
```

## Real Example (todo.ts → commands/router.ts)

**Before:**
- `todo.ts` (~350 lines) mixed `registerTodoTool()`, `registerClankerCommand()`, routing logic in the handler, and all subcommand logic inline

**After:**
- `commands/router.ts` (~240 lines) — `routeCommand()` with `CommandContext` type, 6 handlers (help, eod, dispatch, focus, empty, intercept), handler map with aliases
- `todo.ts` (~120 lines) — Thin registration facade: `registerTodoTool()` and `registerClankerCommand()` only, delegates routing to `commands/router.js`

## Pitfalls

1. **Don't keep I/O in handlers** — Handlers should call into state functions, not open files directly. File reads belong in the repository/store layer.
2. **Dynamic import to avoid module coupling** — Use `await import("./commands/router.js")` in the facade to prevent circular imports at module-evaluation time.
3. **Handler return values must be consistent** — The `boolean` return signals re-render. Don't let some handlers return `undefined`/`void` while others return `false`.
4. **Input normalization in the facade** — Trim and check for empty input *before* calling `routeCommand()`. Don't push whitespace handling into every handler.
5. **Handler aliases vs. normalization** — Aliases (`"--help"`, `"-h"`) in the handler map are simpler than rewriting input before routing. Add them when a subcommand has multiple accepted forms.
6. **`hasUI` is a capability flag, not a user preference** — It signals whether interactive UI channels exist, not whether the user wants a rich view. Test both paths.
7. **Don't export raw handlers from router** — The router's public API should be just `routeCommand()`. Handlers are implementation details.

## Verification

- [ ] `npx tsc --noEmit` passes with zero errors
- [ ] Original file (e.g., `todo.ts`) calls `routeCommand(input, notify, hasUI)` — no inline routing logic remains
- [ ] `commands/router.ts` exports exactly one public function: `routeCommand`
- [ ] Each handler is a standalone function with a single responsibility
- [ ] Handler map includes all aliases (e.g., `"--help"` and `"-h"` alongside `"help"`)
- [ ] Empty input shows the default view (board)
- [ ] Unknown input falls through to natural-language intercept (not an error)
- [ ] Handlers notify through `ctx.notify()`, not through direct `process.stdout.write()` or `ctx.ui.notify()`
- [ ] All callers updated to import from new paths