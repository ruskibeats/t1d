---
name: "survey-pi-extension"
description: "Survey and understand a Pi extension's structure, entry points, components, and configuration. Use when exploring a Pi extension, onboarding to an extension codebase, or understanding how a specific extension registers commands, tools, and UI widgets."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

Use this skill when you need to understand a Pi extension's structure, entry points, configuration, and components. This is useful for:

- Onboarding to a new Pi extension codebase
- Understanding how a specific Pi extension works (commands, tools, widgets)
- Debugging or modifying an existing extension
- Learning patterns from existing extensions before creating a new one

Do **not** use this for installing extensions (use `install-pi-package-with-npm-fallback`) or publishing them (use `publish-existing-project-to-github`).

## Procedure

### 1. Locate the extension directory

Pi extensions typically live under `.pi/extensions/<extension-name>/` in any project root. Use `ls` or `find` to discover them:

```bash
ls .pi/extensions/
```

Each subdirectory is one extension package.

### 2. Read package.json first

Always start with `package.json` — it declares the extension metadata and entry points:

```bash
cat .pi/extensions/<name>/package.json
```

Key fields to extract:
- **`name`** and **`version`**: identity
- **`pi.extensions`** (array): lists entry point file paths — **read every listed file**
- **`type`**: `"module"` (ESM) or `"commonjs"` — affects import syntax

Example:
```json
{
  "name": "clanker-ops-todo",
  "pi": { "extensions": ["./index.ts"] }
}
```

### 3. Read the main entry point

The first file in `pi.extensions` is usually `index.ts`. It exports a default async function accepting the Pi `ExtensionAPI`:

```typescript
export default async function (api: ExtensionAPI): Promise<void> {
```

Look for what the extension **registers**:
- **Slash commands**: `api.commands.register("todos", ...)`
- **Tools**: `api.tools.register("todo", ...)` or loaded from a `tool/` directory
- **UI Widgets**: `api.widgets.register("TodoOverlay", ...)`
- **State handlers**: state management subscriptions

### 4. Survey supporting files

Based on what the entry point imports, read supporting files:

| File/Dir | Purpose |
|----------|---------|
| `config.ts` | Configuration loading, defaults, user preferences |
| `todo.ts`, `todo-overlay.ts` | Core business logic and TUI components |
| `state/` | State management, persistence, replay logic |
| `tool/` | Tool definitions (each file = one tool) |
| `locales/` | Internationalization resources |
| `state/i18n-bridge.ts` | Translation helpers |

### 5. Understand the key exports pattern

Pi extensions follow a module pattern:

- **Default export** (from entry point): main async function `(api: ExtensionAPI) => Promise<void>`
- **Named exports**: component classes, helper functions, configuration constants
- **Tool definitions**: each tool file exports a tool definition object with `name`, `description`, `parameters` schema, and `execute` handler

### 6. Trace the data flow

Answer these questions:
- **Input**: How does the extension receive data? (CLI args, API calls, file reads, user input)
- **Processing**: How does it transform data? (state managers, reducers, event handlers)
- **Output**: How does it present results? (slash command responses, tool results, TUI widget updates)

## Pitfalls

- **Multiple entry points**: Some extensions list several files in `pi.extensions`. Read **all** of them — each registers different capabilities.
- **Missing dependencies**: The extension's own `package.json` may not list all npm deps. Check the project root's `node_modules` or root `package.json`.
- **Tool files referenced from entry point**: Extensions may load tool definitions dynamically (e.g., scanning a `tool/` directory). Read those tool files too.
- **Widget-only extensions**: Some extensions register only TUI widgets without any slash commands or tools. The absence of commands/tools is valid — focus on widget registration instead.
- **TypeScript vs JavaScript**: Extensions are typically `.ts` but can be `.js`. Both work the same; adjust syntax expectations.
- **State persistence**: Some extensions persist state to disk (e.g., `.pi/todo-state.json`). Check state file paths mentioned in state modules.

## Verification

- [ ] You identified the extension's `package.json` and its `pi.extensions` entry points
- [ ] You read all entry point files listed in `pi.extensions`
- [ ] You can name what commands, tools, and/or widgets the extension registers
- [ ] You understand the data flow: input source → processing logic → output mechanism
- [ ] You identified config mechanism (`config.ts`, JSON files, env vars)
- [ ] You can state the extension's purpose and the problem it solves