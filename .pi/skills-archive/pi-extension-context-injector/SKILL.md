---
name: "pi-extension-context-injector"
description: "Build a context injector for a Pi extension that formats a compact work queue or state summary and injects it into LLM context via HTML comments during lifecycle events. Use when your Pi extension manages a work queue (tasks, dispatches, agents) and you want the LLM to be aware of current state without the user running /clanker explicitly."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Pi Extension Context Injector

## When to Use

You are building a Pi extension that manages a work queue (tasks, dispatches, agents, runs) and you want the LLM to be aware of the current queue state without the user having to run a command (`/clanker`, `/status`, `/queue`) explicitly.

The context injector pattern:
1. Formats a compact summary of the current state
2. Wraps it as an HTML comment (`<!-- CLANKER: ... -->`)
3. Hooks into Pi session lifecycle events (session_start, before_turn)
4. The LLM always "sees" the comment in context and acts on it

Use when:
- Building a task/work-queue extension for Pi (Clanker Ops, ticket systems, run queues)
- You want the LLM to proactively offer status updates, flag blockers, or suggest next actions
- The work queue state changes asynchronously (dispatched subagents, time-based completions)

Do NOT use for:
- Static configuration that never changes (no need to re-inject every turn)
- User-specific preferences (they're always available via memory)
- Large state dumps (>1KB will waste context window — keep it compact)

## Architecture

```
state/store.ts (persistent state)
       │
       ▼
context-injector.ts
       │
       ├── formatCompactContext()   → "<!-- CLANKER: 2 active, 5 queued — top: #1 "Deploy" @alice -->"
       ├── formatDetailContext()    → Multi-line HTML comment with sectioned breakdown
       └── planExists(id)           → Helper to flag tasks without plans
       │
       ▼
index.ts (lifecycle events)
       │
       ├── session_start          → Inject detail context
       └── before_turn / notify   → Inject compact context (when state changes)
```

## Procedure

### 1. Build the state access layer

Before you can inject context, you need the state it reflects:

```typescript
// Assuming you have a file-backed store
import { getState } from "./state/store.js";
import { selectTasksByStatus } from "./state/selectors.js";
import { existsSync } from "node:fs";
import { join } from "node:path";
```

### 2. Implement compact context (single-line HTML comment)

This is the primary injection — a single line that fits in the system prompt without adding visual noise:

```typescript
export function formatCompactContext(): string {
  const state = getState();
  const visible = state.tasks.filter((t) => t.status !== "deleted");
  const groups = selectTasksByStatus(state);

  // Top 3 active tasks with owner + plan status
  const active = groups.inProgress.slice(0, 3).map((t) => {
    const owner = t.assigned ? `@${t.assigned.replace(/^@/, "")}` : "";
    const plan = planExists(t.id) ? "" : "⚠no-plan";
    return `#${t.id} "${t.item}"${owner}${plan}`;
  });

  // Aggregate counts
  const failed = visible.filter((t) => t.status === "failed");
  const blocked = visible.filter((t) => (t.blockedBy?.length ?? 0) > 0);

  const parts: string[] = [];
  parts.push(`${groups.inProgress.length} active`);
  parts.push(`${groups.pending.length} queued`);
  if (failed.length) parts.push(`${failed.length} failed`);
  if (groups.completed.length) parts.push(`${groups.completed.length} done`);

  let compact = `<!-- CLANKER: ${parts.join(", ")}`;
  if (active.length) compact += ` — top: ${active.join("; ")}`;
  if (failed.length) compact += ` — ⚠${failed.length} failed`;
  if (blocked.length) compact += ` — ⊘${blocked.length} blocked`;
  compact += ` -->`;

  return compact;
}
```

**Why an HTML comment?** Pi's LLM pipelines skip HTML comments in the visible chat but still process them as context tokens. The comment format:
- Doesn't clutter the visible conversation
- Is parseable by the LLM if it needs the information
- Is clearly structured with a `CLANKER:` prefix for disambiguation

### 3. Implement detail context (multi-line HTML comment)

For session start, use a richer format that the LLM can reference throughout the session:

```typescript
export function formatDetailContext(): string {
  const state = getState();
  const visible = state.tasks.filter((t) => t.status !== "deleted");
  const groups = selectTasksByStatus(state);
  const failed = visible.filter((t) => t.status === "failed");
  const blocked = visible.filter((t) => (t.blockedBy?.length ?? 0) > 0);
  const missingPlans = visible.filter(
    (t) => t.status !== "completed" && !planExists(t.id),
  );

  const lines: string[] = ["", "<!-- CLANKER_OPS", `Project: some-project-name`];

  // Active section
  if (groups.inProgress.length) {
    lines.push("", "Active:");
    for (const t of groups.inProgress) {
      const owner = t.assigned ? ` @${t.assigned}` : "";
      const plan = planExists(t.id) ? "" : " ⚠no-plan";
      lines.push(`  ◐ #${t.id} ${t.item}${owner}${plan}`);
    }
  }

  // Failed section
  if (failed.length) {
    lines.push("", "Failed:");
    for (const t of failed) lines.push(`  ✗ #${t.id} ${t.item}`);
  }

  // Blocked section
  if (blocked.length) {
    lines.push("", "Blocked:");
    for (const t of blocked)
      lines.push(`  ⊘ #${t.id} ${t.item} — blockedBy=${(t.blockedBy ?? []).map((d) => `#${d}`).join(",")}`);
  }

  // No-plan section (limit to 5 to avoid bloat)
  if (missingPlans.length) {
    lines.push("", "Missing plans:");
    for (const t of missingPlans.slice(0, 5))
      lines.push(`  ⚠ #${t.id} ${t.item}`);
  }

  lines.push("-->");
  return lines.join("\n");
}

function planExists(id: number): boolean {
  const planPath = join(process.cwd(), ".pi", "todo-plans", `#${id}_plan.md`);
  return existsSync(planPath);
}
```

### 4. Hook into lifecycle events

In your extension's `index.ts`, register the injector on lifecycle events:

```typescript
import type { ExtensionAPI } from "@pipelessthan3/pi";
import { formatCompactContext, formatDetailContext } from "./injector/context-injector.js";

export function activate(pi: ExtensionAPI): void {
  // Register the context injector as an LLM-callable tool
  // that returns the compact context
  pi.registerTool({
    name: "get-clanker-context",
    description: "Get the current Clanker Ops work queue context",
    handler: () => formatCompactContext(),
  });

  // Or hook into lifecycle events
  // (exact API depends on Pi's ExtensionAPI — the pattern is to
  //  register a callback that's called on each session turn)
}
```

**Key design decisions:**

| Decision | Compact vs Detail | Rationale |
|----------|------------------|-----------|
| Per-turn injection | Compact (single line ~200-300 chars) | Minimal token cost for every LLM interaction |
| Session start | Detail (multi-line ~500-800 chars) | Richer initial context, the LLM won't lose it |
| State change events | Compact re-injection | Keep the LLM current without repeating the full detail |

### 5. Decide injection strategy

**Option A: Per-turn injection** (recommended)
The injector runs before every LLM turn and prepends a compact summary. Token cost is ~50-100 tokens per turn. Pro: always fresh. Con: every turn pays the token cost.

**Option B: On-change injection**
Only re-inject when state changes (new tasks, status transitions, dispatch completions). Pro: saves tokens when nothing changes. Con: more complex implementation (need change detection).

**Option C: Session-start only**
Inject detail context once at session start, never update. Pro: cheapest. Con: LLM goes stale — won't know about tasks that completed during the session.

**Recommendation**: Option A for compact mode (low token cost), with detail mode injected once at session start.

## Pitfalls

### Token budget waste
- Each injection costs tokens even if the LLM doesn't use the information.
- **Mitigation**: Keep compact context under 300 chars (~75 tokens). Use detail context only at session start.

### Stale context after user action
- User runs `/clanker dispatch #5 to @agent`, state changes, but injector hasn't re-run.
- **Mitigation**: After any mutation command, explicitly re-inject context.

### Multi-session desync
- Multiple Pi sessions share the same state file. Session A dispatches a task, Session B's injector sees the update.
- **Mitigation**: This is usually a feature (cross-session awareness), but be aware that injectors read from disk, not from in-memory state.

### Plan file staleness
- The injector checks `planExists()` on every turn. If a plan file is created during the session, the injector picks it up next turn.
- **Pitfall**: On filesystem-heavy environments (NFS, Docker bind mounts), `existsSync` can be slow. Cache plan existence per session and invalidate on mutations.

### Comment escaping
- If task items contain `-->` (HTML comment closing), the injector output will be malformed.
- **Mitigation**: Sanitize task descriptions — replace `-->` with `-- >` or `[end]`:
  ```typescript
  function sanitize(text: string): string {
    return text.replace(/-->/g, "-- >");
  }
  ```

## Verification

```typescript
// Test 1: No tasks → empty/inactive context
function testEmptyState() {
  const ctx = formatCompactContext();
  assert(ctx.includes("0 active"), "Empty state should show 0 active");
  assert(ctx.startsWith("<!--"), "Should be an HTML comment");
  assert(ctx.endsWith("-->"), "Should close HTML comment");
}

// Test 2: Active tasks appear in compact context
function testActiveTasks() {
  // (arrange state with 2 in_progress tasks)
  const ctx = formatCompactContext();
  assert(ctx.includes("2 active"), "Should reflect active count");
  assert(ctx.includes("#1"), "Should include task IDs");
}

// Test 3: Detail context has sections
function testDetailSections() {
  const ctx = formatDetailContext();
  // Should start with CLANKER_OPS marker
  assert(ctx.includes("CLANKER_OPS"), "Detail context should have marker");
  // Check for standard section headers
  if (ctx.includes("Active:")) {
    assert(ctx.includes("◐ #"), "Active items should have glyph prefix");
  }
  if (ctx.includes("Failed:")) {
    assert(ctx.includes("✗ #"), "Failed items should have ✗ prefix");
  }
}

// Test 4: planExists returns correct result
function testPlanExists() {
  // (arrange: write a plan file, then call planExists)
  assert(planExists(1) === true, "Should find existing plan");
  assert(planExists(99999) === false, "Should not find non-existent plan");
}

// Test 5: Sanitization prevents HTML comment breaking
function testSanitization() {
  assert(sanitize("Task --> description") === "Task -- > description");
  assert(sanitize("Normal task") === "Normal task");
}
```