---
name: "pi-extension-programmatic-subagent"
description: "Trigger pi-subagents programmatically from a Pi extension without human copy-paste. Covers the ExtensionAPI limitation (no invokeTool/subagent methods), the actual pi-subagents mechanics (temp JSON config + child_process.spawn + jiti runner), and the two architectural paths for auto-dispatch: output assembled commands for the LLM/Controller, or direct dynamic-import spawn with hybrid fallback for standalone extensions."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

- Building a Pi extension that needs to dispatch subagents automatically
- Debugging why an extension can't programmatically invoke subagent tools
- Converting a manual `/subagent` output flow into true auto-dispatch
- Making a standalone extension that spawns subagents without depending on the full pi-subagents package
- Understanding why `ExtensionAPI` has no `.subagent()` or `.invokeTool()` methods

## Procedure

1. **Acknowledge the ExtensionAPI boundary**: The `@earendil-works/pi-coding-agent` ExtensionAPI only exposes `registerTool`, `registerCommand`, and event hooks. It does NOT expose `invokeTool`, `subagent`, or any programmatic tool-calling interface. There is no built-in way to trigger a subagent directly through the API object.

2. **Understand pi-subagents internals**: The `pi-subagents` package achieves background/async execution by:
   - Writing a JSON config to a temp file
   - Spawning a new Node.js process via `child_process.spawn`
   - Using the jiti TypeScript runner to execute the subagent code
   - This is raw process spawning, not an ExtensionAPI abstraction.

3. **Design the dispatch architecture**: Choose between two execution paths (or a hybrid):
   - **Path A — Controller-Led Assembly**: The extension reads plan + agent definition, assembles the fully-formed subagent invocation (command string or JSON config), and outputs it to the LLM/Controller for manual execution. The extension never spawns itself; it delegates the actual execution to the controller.
   - **Path B — Direct Spawn**: The extension dynamic-imports `pi-subagents` internals (e.g., `executeAsyncSingle`, `executeAsyncChain`) and uses the same spawn pattern directly. This creates detached processes from within the extension.

4. **Implement hybrid fallback (recommended for standalone extensions)**: 
   - Try Path B by dynamic-importing `pi-subagents` utilities
   - If the package is unavailable (standalone extension without the dependency), fall back to a local `spawnRunner` that replicates the same behavior: write temp config → `child_process.spawn` with jiti
   - This ensures the extension works both in rich environments and as a zero-dependency standalone package.

5. **Assemble the invocation payload**: Regardless of path, construct the complete subagent configuration:
   - Agent name and task
   - Reads (files to preload)
   - Output path and mode
   - Context (fresh or fork)
   - Any chain/parallel configuration

6. **Execute and monitor**: 
   - For Path A: emit the assembled command to the controller
   - For Path B: spawn the process, capture the run ID, and optionally monitor with `status` checks

## Pitfalls

- **Assuming ExtensionAPI has a `.subagent()` or `.invokeTool()` method** — it does not; this is the most common misconception.
- **Thinking `pi-subagents` is magically integrated into ExtensionAPI** — it is a separate package that spawns raw Node.js processes.
- **Hard-coding a dependency on `pi-subagents` in `package.json`** for a standalone extension — use dynamic import + fallback to avoid forcing consumers to install the package.
- **Forgetting the jiti TypeScript runner** when replicating the spawn pattern — the spawned process needs jiti to execute `.ts` subagent definitions.
- **Not handling detached process cleanup**, leaving zombie Node processes after subagent completion.
- **Attempting to call `subagent()` from within a subagent execution context** — only the top-level controller can orchestrate subagents.

## Verification

- Extension can dispatch a subagent without requiring the user to manually copy-paste a command
- For Path B: `ps aux | grep jiti` or process monitoring shows spawned subagent processes during execution
- Logs or debug output confirm a temp JSON config file was written immediately before process spawn
- Extension loads and functions in an environment where `pi-subagents` is NOT installed in `node_modules` (test the fallback path)
- For Path A: Controller receives a complete, copy-paste-ready subagent invocation string