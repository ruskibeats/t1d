---
name: "pi-extension-internal-refactoring"
description: "Refactor internal structure of Pi extensions to improve isolation, modularization, and maintainability."
version: 9
created: "2026-05-20"
updated: "2026-05-20"
---
# PI Extension Internal Refactoring

## When to Use
Use when a TypeScript-based Pi extension has become monolithic (code logic interleaved with registration/surface area) and needs better isolation, modularity, and maintainability by separating logic into `tool/`, `state/`, and `view/` layers.

## Procedure
## Procedure

### Phase 0: Domain Glossary First
Before any code refactoring, create a `CONTEXT.md` in the extension root with:
- Core domain concepts (Task, Dispatch, RunId, Plan File, etc.)
- Status/state transition diagram
- Key data structures and their relationships
- Command reference
This establishes the ubiquitous language that guides module naming and boundaries. Without it, you risk extracting modules around the wrong abstractions.

### Phase 1: Branch & Backup
1. Create a git branch for the refactoring: `git checkout -b <name>-architecture-improvements`
2. Verify clean state: `git status`
3. Commit any existing work first

### Phase 2: Deepen Core Modules (Bottom-Up)
Work bottom-up — start with the most fundamental data modules and work outward:

1. **State/Reducer modules** — Extract from the main state reducer:
   - `Validator` (transition validation rules)
   - `Factory` (entity creation with defaults)
   - `Mutator` (field-wise mutation logic)
   - `Repository` (file I/O isolation, with testable interface)
   - Keep the original reducer as a thin facade delegating to these

2. **View/Presenter modules** — Extract from board/renderer files:
   - `BoardModel` or `Presenter` (data transformation, grouping, formatting logic)
   - `TextUtils` (ANSI formatting, padding, truncation utilities)
   - Keep the original view file as a thin facade

3. **Service/Dispatch modules** — Extract from spawner/background files:
   - `Resolver` (path resolution logic)
   - `ConfigBuilder` (config construction)
   - `ProcessSpawner` (subprocess lifecycle)
   - Keep the original spawner as a thin facade

4. **Event/Intercom modules** — Extract from intercom handlers:
   - `EventTypes` (canonical event type definitions + classifier)
   - `PlanAudit` (audit/log formatting)
   - `StateUpdater` (event-to-state mapping)
   - Keep the original intercom handler as a thin facade

### Phase 3: Extract Command Router
After deepening all inner modules, extract the command routing logic from the main entry point:

1. Create a `commands/` directory inside the extension root

2. Define shared handler infrastructure at the top of `commands/router.ts`:
   ```typescript
   // Shared context passed to every handler
   export interface CommandContext {
     input: string;          // Raw user input
     subcommand: string;     // Parsed subcommand (first token)
     notify: (msg: string, level: string) => void;  // Notification callback
     hasUI: boolean;         // Whether interactive UI is available
   }

   // Handler signature — each handler receives context and returns whether
   // the board/UI should be re-rendered
   type Handler = (ctx: CommandContext) => Promise<boolean>;
   ```

3. Extract each named subcommand handler as a standalone async function matching the `Handler` type:
   ```typescript
   async function handleHelp(ctx: CommandContext): Promise<boolean> {
     ctx.notify(HELP_TEXT, "info");
     return false; // No re-render needed
   }

   async function handleList(ctx: CommandContext): Promise<boolean> {
     const results = listItems(getState());
     ctx.notify(formatResults(results), "info");
     return false;
   }

   async function handleCreate(ctx: CommandContext): Promise<boolean> {
     // Parse args, create item, commit state
     const result = applyMutation(getState(), "create", { ... });
     commitState(result.state);
     ctx.notify(`✅ Created: ${ctx.input}`, "info");
     return true; // Re-render board
   }
   ```

4. Extract help text and constants to the top of `router.ts` (or a separate `commands/help.ts` if large):
   ```typescript
   const HELP_TEXT = `╭─── Commands ───╮
   │ /app help     Show help
   │ /app list     List items
   │ /app create   Create item
   ╰────────────────╯`;
   ```

5. Build a dispatch map — a `Record<string, Handler>` that maps each subcommand name to its handler:
   ```typescript
   const handlers: Record<string, Handler> = {
     help: handleHelp,
     "--help": handleHelp,
     "-h": handleHelp,
     list: handleList,
     create: handleCreate,
   };
   ```

6. Implement the main `routeCommand` function that:
   - Routes to specific handlers for known subcommands
   - Falls back to a default handler (e.g., show board, or natural language interception)
   - Re-renders UI when handlers return `true`

   ```typescript
   export async function routeCommand(
     input: string,
     notify: (msg: string, level: string) => void,
     hasUI: boolean,
   ): Promise<void> {
     const subcommand = input.split(" ")[0].toLowerCase();
     const ctx: CommandContext = { input, subcommand, notify, hasUI };

     // Empty command — show default view
     if (!input) {
       await handleDefault(ctx);
       return;
     }

     // Known subcommand
     const handler = handlers[subcommand];
     if (handler) {
       await handler(ctx);
       return;
     }

     // Natural language intercept — treat as new item or error
     await handleIntercept(ctx);

     // Re-render board after interception if possible
     if (hasUI) {
       try { notify(renderBoard(getState()), "info"); } catch { /* noop */ }
     }
   }
   ```

7. Reduce the main entry point (`todo.ts` or equivalent) to a thin registration shell:
   ```typescript
   export function registerClankerCommand(pi: ExtensionAPI): void {
     pi.registerCommand(COMMAND_NAME, {
       description: "...",
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

8. **Keep the original file's re-exports intact** so that pre-refactor consumers (overlay components, tests, index.ts) continue to import from the original path without breaking.

**Key design decisions:**
- The `Handler` return type is `Promise<boolean>` — `true` signals the caller to re-render the board/UI, `false` means no re-render needed. This prevents redundant UI refreshes for read-only commands.
- The `CommandContext` encapsulates all shared dependencies (notifications, UI flag), keeping handlers pure w.r.t. their environment and making them easy to test with a mock context.
- The dispatch map pattern (`Record<string, Handler>`) makes it trivial to add new subcommands — just write a handler function and add one entry to the map.
- Dynamic import (`await import("./commands/router.js")`) in the registration shell avoids loading the router module at extension startup, keeping the hot reload fast.

### Phase 4: Implement the Op/Response-Envelope Pattern
After extracting reducer sub-modules (Validator, Factory, Mutator), wire the reducer to return a structured `Op` tagged union instead of raw strings. Create a dedicated `tool/response-envelope.ts` with a `formatContent` function using an exhaustive compiler-enforced `switch` on `Op.kind`, and a `buildToolResult` function that produces the replay-compatible `details` snapshot. This prevents Op/Formatter drift — see `global:pi-extension-op-response-envelope` for the full procedure.
## Procedure

### Phase 0: Domain Glossary First
Before any code refactoring, create a `CONTEXT.md` in the extension root with:
- Core domain concepts (Task, Dispatch, RunId, Plan File, etc.)
- Status/state transition diagram
- Key data structures and their relationships
- Command reference
This establishes the ubiquitous language that guides module naming and boundaries. Without it, you risk extracting modules around the wrong abstractions.

### Phase 1: Branch & Backup
1. Create a git branch for the refactoring: `git checkout -b <name>-architecture-improvements`
2. Verify clean state: `git status`
3. Commit any existing work first

### Phase 2: Deepen Core Modules (Bottom-Up)
Work bottom-up — start with the most fundamental data modules and work outward:

1. **State/Reducer modules** — Extract from the main state reducer:
   - `Validator` (transition validation rules)
   - `Factory` (entity creation with defaults)
   - `Mutator` (field-wise mutation logic)
   - `Repository` (file I/O isolation, with testable interface)
   - Keep the original reducer as a thin facade delegating to these

2. **View/Presenter modules** — Extract from board/renderer files:
   - `BoardModel` or `Presenter` (data transformation, grouping, formatting logic)
   - `TextUtils` (ANSI formatting, padding, truncation utilities)
   - Keep the original view file as a thin facade

3. **Service/Dispatch modules** — Extract from spawner/background files:
   - `Resolver` (path resolution logic)
   - `ConfigBuilder` (config construction)
   - `ProcessSpawner` (subprocess lifecycle)
   - Keep the original spawner as a thin facade

4. **Event/Intercom modules** — Extract from intercom handlers:
   - `EventTypes` (canonical event type definitions + classifier)
   - `PlanAudit` (audit/log formatting)
   - `StateUpdater` (event-to-state mapping)
   - Keep the original intercom handler as a thin facade

### Phase 3: Extract Command Router
After deepening all inner modules, extract the command routing logic from the main entry point:
1. Create a `commands/` directory
2. Extract each named subcommand handler into a map
3. Extract help text and constants
4. Create a `router.ts` that maps command names to handlers
5. Reduce the main entry point to thin registration shell + re-exports

### Phase 4: Implement the Op/Response-Envelope Pattern
After extracting reducer sub-modules (Validator, Factory, Mutator), wire the reducer to return a structured `Op` tagged union instead of raw strings. Create a dedicated `tool/response-envelope.ts` with a `formatContent` function using an exhaustive compiler-enforced `switch` on `Op.kind`, and a `buildToolResult` function that produces the replay-compatible `details` snapshot. This prevents Op/Formatter drift — see `global:pi-extension-op-response-envelope` for the full procedure.
## Pitfalls
-   **Breaking Importers**: Renaming files without re-exporting from the original location, causing `ImportError` or `ModuleNotFound`.
-   **Circular Imports**: Inter-layer dependencies that create cycles. Fix by moving shared logic to a `shared/` or `types/` folder. This is especially common when state sub-modules (Validator, Factory, Mutator) each import from each other — keep them leaf modules that import only types and the base `Task` interface.
-   **Registration Path Changes**: Changing the persistence keys (used by `replay.ts` or `permissions.jsonc`) accidentally by renaming constants.
-   **Module Explosion**: Creating too many tiny files with single functions. Keep the granularity at "one conceptual concern per module" — a Validator, a Factory, a Mutator, a Repository — not one file per function.
-   **Over-Abstracting Simple Logic**: Not every `if` statement needs a dedicated module. Extract only when the logic (a) has multiple callers, (b) has complex branching, or (c) needs independent testing. A simple two-line validation belongs inline.
-   **Forgetting Token Budget**: Each new module file adds to startup cost. Keep `state/` and `view/` focused on what actually needs isolation. If total state logic is <50 lines, consider keeping it in one file until it grows.
-   **Op/Formatter Drift**: After extracting an `Op` tagged union and formatter, it's easy to add a new reducer action but forget to add the corresponding `Op` variant and formatter branch. The compiler catches this if you use a closed `switch` with exhaustive checking (`noImplicitReturns` or explicit `never` return). Without this, drift silently produces `undefined` output for new actions.
-   **Cycle Detection Complexity**: When extracting the `UpdateMutator`, the cycle detection algorithm (`detectCycle`) for blockedBy/dependency graphs is non-trivial — it requires DFS over the full task list with visiting/visited state tracking. Don't inline this in the mutator; extract it as a pure function in a `task-graph.ts` module so it can be unit-tested independently.
-   **Event Group ID Collisions**: If the extension tracks correlated events (e.g., dispatch run groups), use a timestamp-based UUID (`${Date.now()}-${randomBytes(4).toString("hex")}`) for group IDs rather than sequential integers, to avoid collisions across concurrent mutations.
## Verification
- Run the Pi extension (auto-reload via `/reload`).
- Verify slash command availability.
- Verify widget UI renders (`TodoOverlay`).
- Test tool functionality (`todo` tool).
- Inspect logs to ensure no `ModuleNotFound` warnings were introduced during import path migration.
- **Deep layer verification**:
    - Check that `state/` has no circular imports: `npx madge --circular --extensions ts .pi/extensions/<name>/state/`
    - Verify each state sub-module has a single, clear responsibility (Validator validates, Factory creates, Mutator mutates).
    - Verify TransitionValidator is imported by the reducer and UpdateMutator (not redundant copies).
    - Ensure the original reducer file is *lighter* after extraction — if it's still a wall of code, extraction wasn't complete.
    - Run the extension's test suite if one exists.
    - Verify that CONTEXT.md (if created) accurately describes the module architecture and would help an onboarding developer.
- **Board rendering verification (Pi TUI-specific)**:
    - Run `/clanker` and visually inspect the right-edge formatting of the board border — ensure no characters overflow past the rightmost `╯`/`┤`/`╰` borders.
    - Check the title row: the "N done · M in progress" summary should sit cleanly at the end of the title line without overflowing the right border.
    - Verify that the Plan column shows actual filenames like `#120_plan.md` (not just `yes`/`true`/`no`).
    - Resize the terminal to a narrow width (e.g., 80 columns) and a wide width (e.g., 180 columns) — the board should not break at either extreme.
    - Verify column alignment: all rows should have their columns aligned vertically under the column headers.
    - Check that status icons (○●✓✕) render correctly and match the task status.
    - Verify the board hides deleted/tombstoned tasks from the active view.
    - If a focus filter is supported, test `/clanker focus <term>` and verify only matching tasks appear.
    - Check that intercom-handler events (dispatch, complete, error) still update the task state correctly by dispatching a test task.