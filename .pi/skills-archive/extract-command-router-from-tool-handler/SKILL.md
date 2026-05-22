---
name: "extract-command-router-from-tool-handler"
description: "Extract command routing logic from a monolithic tool handler into a dedicated router module using a Handler type and handlers record. Use when a tool file grows beyond ~200 lines and mixes command routing with execution logic."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Extract a Command Router From a Tool Handler

## When to Use

Extract command routing logic from a monolithic tool handler file into a dedicated router module when:

- A tool handler file exceeds ~200 lines
- The file mixes command routing (if/else chains, switch/case) with execution logic
- You need to add new subcommands without bloating the handler further
- Unit tests are hard to write because testing routing requires running the full handler
- Multiple handlers share routing logic (commands, subcommands, flags)

Do NOT use for:
- Handlers with fewer than 3-4 subcommands that are unlikely to grow
- Trivial routing (single command, no subcommands)
- First-time experimentation — let the handler's subcommand shape settle before extracting

## Procedure

### Step 1 — Identify the routing logic

Locate the switch/case or if/else chain that dispatches by subcommand. This is usually:

```typescript
// In your tool file (e.g., todo.ts)
function handleCommand(input: string): string {
  const parts = input.split(" ");
  const cmd = parts[0];
  if (cmd === "board") return renderBoard(parts.slice(1));
  else if (cmd === "dispatch") return handleDispatch(parts.slice(1));
  else if (cmd === "eod") return handleEod(parts.slice(1));
  // ... growing chain
  else return "Unknown command";
}
```

**Evidence**: Grep the file for `else if`, `switch`, or `case` to find the routing boundary.

### Step 2 — Define a Handler type

Create a `Handler` type that captures the calling convention. Keep it specific enough for type safety but generic enough that all handlers can use it.

```typescript
// commands/router.ts
export interface CommandContext {
  input: string;
  args: string[];
  taskId?: number;
  hasUI: boolean;
}

export type Handler = (ctx: CommandContext) => string | Promise<string>;
```

**Key decisions**:
- **Return type**: `string | Promise<string>` covers both sync and async handlers. If all handlers are async, use `Promise<string>`.
- **Context shape**: Pass parsed args AND raw input so handlers can re-parse if needed.
- **Error signaling**: Use a sentinel value (empty string, `"ERR"`) or a discriminated result type.

**Pitfall**: Do NOT make the Handler return `void` or `undefined` — every subcommand should produce some output. If a handler has nothing to say, return an empty string and let the router ignore it.

### Step 3 — Build the handlers record

Create a record mapping command names to Handler functions:

```typescript
// commands/router.ts
export const handlers: Record<string, Handler> = {};
```

Then extract each handler from the original file and register it:

```typescript
// commands/router.ts
handlers["board"] = async (ctx: CommandContext): Promise<string> => {
  // extracted from the original tool file
  return renderBoard(ctx.args);
};

handlers["dispatch"] = async (ctx: CommandContext): Promise<string> => {
  // ...
};

handlers["eod"] = async (ctx: CommandContext): Promise<string> => {
  // ...
};
```

**Key decisions**:
- **Lazy import handlers** from separate files if they're large: `import { handleBoard } from "./handlers/board.js"` and register in the record.
- **Single file for small handlers**: Keep all handlers in `router.ts` if each is <30 lines.
- **Duplicate command names**: Later registrations overwrite earlier ones. If supporting aliases, add a separate `aliases` map.

### Step 4 — Create the route function

```typescript
// commands/router.ts
export const ERR_UNKNOWN_COMMAND = "Unknown subcommand";
export const ERR_REQUIRES_INTERACTIVE = "This command requires an interactive session";

export async function routeCommand(ctx: CommandContext): Promise<string> {
  const cmd = ctx.args[0];
  if (!cmd) return ERR_UNKNOWN_COMMAND;

  const handler = handlers[cmd];
  if (!handler) return ERR_UNKNOWN_COMMAND;

  return handler(ctx);
}
```

**Interactive-only guard** (optional but common): Some subcommands only make sense in interactive TUI mode. Check before dispatching:

```typescript
export const INTERACTIVE_ONLY = new Set(["focus", "edit"]);

export async function routeCommand(ctx: CommandContext): Promise<string> {
  const cmd = ctx.args[0];
  if (!cmd) return ERR_UNKNOWN_COMMAND;

  if (INTERACTIVE_ONLY.has(cmd) && !ctx.hasUI) {
    return ERR_REQUIRES_INTERACTIVE;
  }

  const handler = handlers[cmd];
  if (!handler) return ERR_UNKNOWN_COMMAND;

  return handler(ctx);
}
```

### Step 5 — Refactor the original tool file

The original tool file becomes a thin caller:

```typescript
// todo.ts — after extraction
import { routeCommand, CommandContext } from "./commands/router.js";

async function handleInput(input: string, hasUI: boolean): Promise<string> {
  const ctx: CommandContext = {
    input,
    args: input.split(/\s+/).filter(Boolean),
    hasUI,
  };
  return routeCommand(ctx);
}
```

**Save the original's public exports**: If other files import `handleInput`, keep its name and signature stable. The extraction is internal — the public API does not change.

### Step 6 — Update tests

- **Test the router directly**: Call `routeCommand({ args: ["board"], hasUI: true })` and assert the result. No need to go through the original handler.
- **Test unknown command**: `routeCommand({ args: ["nonexistent"], hasUI: false })` → `ERR_UNKNOWN_COMMAND`.
- **Test interactive guard**: `routeCommand({ args: ["focus"], hasUI: false })` → `ERR_REQUIRES_INTERACTIVE`.
- **Test each handler independently**: Import handlers directly or through the record.
- **Test the original entry point**: Verify it still works (smoke test).

```typescript
// router.test.ts
import { routeCommand, ERR_UNKNOWN_COMMAND, ERR_REQUIRES_INTERACTIVE } from "./commands/router.js";

describe("routeCommand", () => {
  it("routes board subcommand", async () => {
    const result = await routeCommand({ args: ["board"], hasUI: true });
    expect(result).not.toBe(ERR_UNKNOWN_COMMAND);
  });

  it("returns unknown for nonexistent subcommand", async () => {
    const result = await routeCommand({ args: ["slartibartfast"], hasUI: true });
    expect(result).toBe(ERR_UNKNOWN_COMMAND);
  });
});
```

## Pitfalls

- **Over-splitting**: If each handler file is a single 5-line function with a 50-line import block, don't extract. Keep small handlers in the router file and extract only when a handler exceeds ~50 lines.
- **Circular dependencies**: Router files import handlers; handlers should NOT import the router. If a handler needs routing utilities, extract those into a shared `utils.ts`.
- **Breaking the public API**: If the original file's functions are imported by tests or other modules, keep the same export surface. Add the router as a new export; don't remove originals until callers migrate.
- **Inconsistent error signaling**: Choose ONE pattern for errors (sentinel strings, thrown exceptions, or Result types). Don't mix — some handlers returning `"ERR"` strings while others throw will make error handling fragile.
- **Missing handler registration**: After extracting a handler to a new file, remember to import and register it in the `handlers` record. A common mistake is to create the file but forget the registration line.
- **Case sensitivity**: Decide upfront whether subcommands are case-sensitive. If `"Board"` should work, normalize in the route function: `const cmd = ctx.args[0].toLowerCase()`.

## Verification

```bash
# TypeScript compiles cleanly
npx tsc --noEmit

# Original tool file is now thin (<100 lines ideally)
wc -l path/to/original-tool.ts

# Router file exists with clear structure
wc -l path/to/commands/router.ts

# No handlers registered twice (unique keys)
grep -c 'handlers\[' path/to/commands/router.ts
# Should be less than or equal to expected handler count

# Public API surface is unchanged
grep "^export" path/to/original-tool.ts

# Router tests pass
npx vitest run path/to/commands/router.test.ts 2>/dev/null || npx jest path/to/commands/router.test.ts 2>/dev/null || npx mocha path/to/commands/router.test.ts
```