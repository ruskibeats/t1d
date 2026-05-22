---
name: "replay-state-from-session-branch"
description: "Recover application state from pi session history by walking the session branch, finding the latest valid state snapshot, and merging with persisted state files. Use when building pi extensions that need to restore state across sessions or recover from crashes."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

- Building a pi extension that persists state across sessions
- Recovering state after a crash or session restart
- Merging state from session history with persisted files
- Reconstructing the latest known-good state from git/session branch

## Procedure

### 1. Define State Shape and Discriminator

```typescript
interface MyState {
  tasks: Task[];
  nextId: number;
}

interface TaskDetails {
  tasks: Task[];
  nextId: number;
}

// Discriminator to validate entry shape from branch
export function isTaskDetails(value: unknown): value is TaskDetails {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return Array.isArray(v.tasks) && typeof v.nextId === "number";
}
```

### 2. Walk Session Branch for Latest Snapshot

```typescript
export function replayFromBranch(ctx: { 
  sessionManager: { getBranch(): Iterable<unknown> } 
}): MyState {
  let result: MyState = { tasks: [], nextId: 1 };
  
  for (const entry of ctx.sessionManager.getBranch()) {
    const e = entry as { 
      type?: string; 
      message?: { 
        role?: string; 
        toolName?: string; 
        details?: unknown 
      } 
    };
    
    // Filter for toolResult with correct toolName and valid shape
    if (e.type !== "message") continue;
    const msg = e.message;
    if (!msg || msg.role !== "toolResult" || msg.toolName !== "todo") continue;
    if (!isTaskDetails(msg.details)) continue;
    
    // Last write wins (most recent snapshot)
    result = {
      tasks: msg.details.tasks.map(t => ({ ...t })),
      nextId: msg.details.nextId,
    };
  }
  
  return result;
}
```

### 3. Merge Replayed State with Persisted File

```typescript
export function replaceState(next: MyState): void {
  const json = readJsonState(); // From .pi/state.json
  
  if (json && json.tasks.length > 0) {
    // File has data - merge with replayed state
    const merged = mergeStates(next, json.tasks);
    const clean = merged.filter(t => t.status !== "deleted");
    commitState({ tasks: clean, nextId: deriveNextId(clean) });
  } else if (next.tasks.length > 0) {
    // No file but replayed state exists
    const clean = next.tasks.filter(t => t.status !== "deleted");
    commitState({ tasks: clean, nextId: next.nextId });
  }
  // Never write empty state over valid data
}
```

### 4. Implement State-Aware Merge

```typescript
function mergeStates(replayed: MyState, currentItems: Task[]): Task[] {
  const currentMap = new Map(currentItems.map(t => [t.id, t]));
  const replayedMap = new Map(replayed.tasks.map(t => [t.id, t]));
  
  const allIds = new Set([...currentMap.keys(), ...replayedMap.keys()]);
  const merged: Task[] = [];
  
  for (const id of allIds) {
    const current = currentMap.get(id);
    const replayedTask = replayedMap.get(id);
    
    if (!current) {
      merged.push(replayedTask!);
    } else if (!replayedTask) {
      merged.push(current);
    } else {
      // Compare updatedAt timestamps - newer wins
      const currentTs = new Date(current.updatedAt).getTime();
      const replayedTs = new Date(replayedTask.updatedAt).getTime();
      merged.push(replayedTs > currentTs ? replayedTask : current);
    }
  }
  
  return merged.sort((a, b) => a.id - b.id);
}
```

## Pitfalls

1. **Never overwrite valid data with empty state** - If replay finds no matching entries but the JSON file has valid data, keep the file data
2. **Always filter deleted/tombstoned items** - Remove tasks with `status === "deleted"` before committing to prevent pollution
3. **Deep copy objects** - Use `.map(t => ({ ...t }))` to avoid mutating branch snapshots
4. **Handle corrupt branch entries gracefully** - Use discriminator functions and skip invalid entries silently
5. **Timestamp comparison requires parsing** - Use `new Date(str).getTime()` not string comparison

## Verification

- [ ] `replayFromBranch` returns minimal state when no matching entries exist in branch
- [ ] Deep copy prevents mutation of branch snapshot data
- [ ] `replaceState` merges replayed and file state correctly (newer wins)
- [ ] Deleted/tombstoned tasks are filtered before committing
- [ ] Empty state does not overwrite valid persisted file data
- [ ] Timestamp comparison correctly identifies newer state