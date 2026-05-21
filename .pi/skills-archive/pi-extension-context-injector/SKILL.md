---
name: "pi-extension-context-injector"
description: "Inject a compact live-state summary as HTML comments into LLM context via session lifecycle hooks in a Pi extension. Use when building a stateful Pi extension that needs the LLM to be always aware of the current work queue, task board, or entity status without requiring explicit commands (e.g., /clanker board, /status). The pattern creates two modes: a compact single-line HTML comment for frequent injection and a multi-line detail block for session initialization."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Pi Extension Context Injector

Inject a compact live-state summary as HTML comments into LLM context via session lifecycle hooks in a Pi extension.

## When to Use

- The extension maintains a stateful entity collection (tasks, tickets, boards, items)
- The LLM should always know the current queue/status without running explicit commands
- You have session lifecycle hooks available (session_start, session_init)
- You need both a compact summary (for frequent injection) and a detail view (for init)

Do NOT use this for:
- One-shot status commands — just return the result inline
- Extensions without a state store or selectors
- When the full board view is always needed — keep it in /command output

## Procedure

### 1. Create the injector module

Create `injector/context-injector.ts` with two formatters:

**Compact formatter** (`formatCompactContext`): Returns a single-line HTML comment.
- Count tasks grouped by status (active, queued, failed, done)
- Include top active items with IDs and owners
- Flag anomalies (failed tasks, blocked tasks, missing plans)
- Keep under ~400 chars to avoid prompt bloat

**Detail formatter** (`formatDetailContext`): Returns a multi-line HTML comment block.
- Section headers for each status group
- Each item on its own line with status icon + ID + description
- Call out known anomalies (no-plan, blocked-by, failed)
- Wrap entire block in `<!-- CLANKER_OPS ... -->`

```typescript
// Compact: single-line HTML comment for frequent injection
export function formatCompactContext(): string {
    const state = getState();
    const visible = state.tasks.filter(t => t.status !== "deleted");
    const groups = selectTasksByStatus(state);
    
    const active = groups.inProgress.slice(0, 3).map(t => {
        const owner = t.assigned ? ` @${t.assigned.replace(/^@/, "")}` : "";
        return `#${t.id} "${t.item}"${owner}`;
    });
    
    const failed = visible.filter(t => t.status === "failed");
    const blocked = visible.filter(t => (t.blockedBy?.length ?? 0) > 0);
    
    const parts: string[] = [];
    parts.push(`${groups.inProgress.length} active`);
    parts.push(`${groups.pending.length} queued`);
    if (failed.length) parts.push(`${failed.length} failed`);
    
    let compact = `<!-- CTX: ${parts.join(", ")}`;
    if (active.length) compact += ` — top: ${active.join("; ")}`;
    if (failed.length) compact += ` — ⚠${failed.length} failed`;
    compact += ` -->`;
    
    return compact;
}
```

### 2. Hook into session lifecycle

In the extension `index.ts`, register lifecycle hooks:

```typescript
// On session start: inject full detail context
pi.on("session_start", (session) => {
    const detail = formatDetailContext();
    session.setSystemPromptInjection(detail);
});

// On state change: inject compact context (if re-injection is supported)
stateStore.on("change", () => {
    const compact = formatCompactContext();
    // Re-inject compact summary via available lifecycle event
});
```

### 3. Structure the HTML comment format

- Use `<!-- KEY: ... -->` format (HTML comments are invisible to rendering)
- Use emoji indicators: ◐ in-progress, ✗ failed, ⊘ blocked, ⚠ warning
- Always include counts, not just raw items
- The compact form should fit on one line
- The detail form can be a full `<!-- SECTION -->` block with line breaks

### 4. Integrate with selectors

Create selectors that the injector can use:
- `selectTasksByStatus(state)` → group tasks by their status field
- `planExists(taskId)` → check if a supporting plan/spec file exists

## Pitfalls

- **Comment bloat** — Keep compact form under ~400 chars. If the queue is large, truncate to top 3-5 items and use a count for the rest.
- **Stale comments** — If the injection happens only at session start, the comment goes stale. Hook into state-change events for re-injection when the platform supports it.
- **Redundant information** — Don't include information the /command handler already shows. The injector is a teaser, not a replacement.
- **Broken HTML comments** — Ensure no `-->` appears inside the comment content itself. Escape or trim task descriptions to prevent premature comment closure.
- **Performance** — The injector runs synchronously. If the state store is large (1000+ items), add limits/slicing before formatting.

## Verification

- [ ] `formatCompactContext()` returns a valid single-line HTML comment (`<!-- ... -->`)
- [ ] `formatDetailContext()` returns a valid multi-line HTML comment block
- [ ] The compact form includes counts for each relevant status group
- [ ] The detail form lists individual items with IDs and status icons
- [ ] Anomalies (failed tasks, blocked items) are visually flagged
- [ ] The comment is injected into the LLM context at session start
- [ ] After state changes, the comment content reflects the new state (or is flagged as stale)
- [ ] Total compact comment size is under 600 chars
- [ ] Task descriptions are safe against premature HTML comment closure