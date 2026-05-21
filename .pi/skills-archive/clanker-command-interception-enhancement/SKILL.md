---
name: "clanker-command-interception-enhancement"
description: "Enhance the /clanker command handler with intelligent input interception, EOD reporting, and filtered board views. Covers the pattern of parsing subcommands, intercepting unrecognized natural language input as new work items, generating daily summary reports, and supporting focus/filter modes for the board."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use

Use this skill when enhancing the `/clanker` command handler in `.pi/extensions/clanker-ops/todo.ts` to:

- Intercept unrecognized natural language input as new work items (smart task creation)
- Add `/clanker eod` for end-of-day completion reports
- Add `/clanker focus &lt;filter&gt;` for filtered board views
- Add any new subcommand to the Clanker Ops command handler

**Trigger phrases**: "add intelligent task interception", "enhance clanker command", "add eod report", "add focus mode", "natural language task creation", "make /clanker smarter"

## Procedure

### Step 1: Restructure the command handler for subcommand parsing

The `/clanker` command handler currently takes raw string args. Restructure it to:

```typescript
handler: async (args, ctx) => {
    const input = typeof args === "string" ? args.trim() : "";
    const subcommand = input.split(" ")[0].toLowerCase();
    
    // Handle empty input (no args) → show board
    if (!input) {
        // fall through to board display
    }
    // Handle known subcommands first
    else if (subcommand === "help" || ...) { ... }
    else if (subcommand === "eod") { ... }  // new subcommand
    else if (subcommand !== "focus") {
        // INTERCEPTION: unrecognized input → new work item
    }
}
```

**Key**: Check known subcommands BEFORE the interception fallthrough. The `subcommand !== "focus"` guard ensures `focus` falls through to board display with filter, not interception.

### Step 2: Add EOD report subcommand

```typescript
else if (subcommand === "eod") {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const state = getState();
    const completedTasks = state.tasks.filter(
        (t) => t.status === "completed" && new Date(t.updatedAt) > yesterday
    );

    const report = [
        `# Clanker Ops EOD Report - ${now.toLocaleDateString()}`,
        `## Completed Tasks (Last 24h)`,
        ...completedTasks.map(t => `- [x] #${t.id} ${t.subject}`),
        completedTasks.length === 0 ? "_No tasks completed in the last 24h._" : ""
    ].join("\n");

    ctx.ui.notify(report, "info");
    return;
}
```

**Pitfalls**:
- The state structure uses `tasks` array — ensure you're reading the correct key from `todo-state.json` (e.g., `items` vs `tasks` depending on which state representation you have)
- Handle the empty completed tasks case gracefully
- Use `toLocaleDateString()` for human-readable dates

### Step 3: Add intelligent input interception

After all known subcommand checks, intercept unrecognized input:

```typescript
else if (subcommand !== "focus") {
    // Treat unrecognized input as a new work item
    const result = applyTaskMutation(getState(), "create", { subject: input });
    commitState(result.state);
    ctx.ui.notify(`✅ Added: ${input}`, "info");
    // Fall through to show the updated board
}
```

**Pitfalls**:
- Must check `subcommand !== "focus"` AFTER the other subcommand checks — otherwise `/clanker focus X` would be intercepted as a new task named "focus X"
- The `create` mutation expects `subject` but the board items use `item` — check your mutation function's parameter mapping
- Don't return after interception — fall through to show the updated board so the user sees their new item

### Step 4: Add focus/filter mode for the board

Replace the simple board renderer with a filtered version when `focus` subcommand is used:

```typescript
// Before rendering the board
let filteredTasks = selectVisibleTasks(getState());

if (subcommand === "focus" && input.split(" ").length > 1) {
    const filter = input.split(" ")[1];
    filteredTasks = selectFilteredTasks(getState(), filter);
}

const board = renderClankerBoard(process.stdout.columns || 120, [...filteredTasks]);
ctx.ui.notify(board, "info");
```

Update `renderClankerBoard` to accept an optional filtered task list parameter:

```typescript
export function renderClankerBoard(columns: number, tasks?: Task[]): string {
    const state = getState();
    const visible = tasks || selectVisibleTasks(state);
    // ... render using visible instead of selectVisibleTasks(state)
}
```

### Step 5: Verify the changes

Test each behavior:

| Input | Expected Behavior |
|-------|------------------|
| `/clanker` | Shows the full work board |
| `/clanker help` | Shows help text |
| `/clanker eod` | Shows EOD report with recent completions |
| `/clanker focus @worker` | Shows board filtered to @worker tasks |
| `/clanker Build login page` | Creates new task "Build login page" and shows board |
| `/clanker random input` | Creates new task "random input" |

## Pitfalls

### Subcommand ordering matters
Known subcommands (`help`, `eod`, `focus`) must be checked BEFORE the interception fallthrough. If you reverse the order, `/clanker help` creates a task named "help" instead of showing help text.

### Focus guard is critical
The `subcommand !== "focus"` check must use `!==`, not `===`. Only `focus` should be excluded from interception and allowed to fall through to the board filter logic.

### Commit state after mutation
After `applyTaskMutation`, you MUST call `commitState(result.state)` to persist the change. Without it, the task appears in the UI notification but isn't saved to `todo-state.json`.

### Empty input handling
When no args are passed (`/clanker`), `input` is `""` and `subcommand` becomes `""` — this should fall through to the default board display, NOT be intercepted as a new task with empty subject.

### String vs object args
Pi command handlers can receive both `string` and `object` args. The code currently handles only string args — if the caller passes an object, `typeof args === "string"` fails and `input` becomes `""`, falling through to board display.

## Verification

- [ ] `/clanker` (no args) → shows full board without creating a task
- [ ] `/clanker help` → shows help text, not a new task
- [ ] `/clanker eod` → shows EOD report (or "No tasks completed" if none)
- [ ] `/clanker focus @worker` → shows board filtered to @worker tasks
- [ ] `/clanker Build the login page` → creates task with subject "Build the login page" and shows board
- [ ] After interception, `todo-state.json` contains the new item with `status: "pending"`
- [ ] Focus mode with invalid filter gracefully falls back to showing all visible tasks
- [ ] EOD report only shows tasks completed in last 24h, not all completed tasks