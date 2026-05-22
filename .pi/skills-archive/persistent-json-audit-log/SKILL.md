---
name: "persistent-json-audit-log"
description: "Build a crash-safe, persistent JSON audit log for tracking operations (dispatches, executions, deployments) with atomic writes, structured entries, mutation functions, and query/format helpers. Transferable to any Node.js project."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Persistent JSON Audit Log

Build a crash-safe, persistent JSON audit log for tracking operations — dispatches, executions, deployments, or any sequential actions. Uses atomic writes (write to `.tmp` → `renameSync`) to prevent partial/corrupt log files.

## When to Use

- You need a durable, human-readable audit trail of operations (task dispatches, deployment runs, job executions).
- You want crash-safe writes — no partial/corrupt files if the process dies mid-write.
- You need structured entries that support query, format, and rollup.

## Architecture

```
log.js
├── JSON file on disk (e.g., .project/dispatch-log.json)
├── Entry array (most recent appended last)
├── Read/Write: readFileSync → mutate → write .tmp → renameSync
├── Mutations: logAction(), logHeartbeat(), logCompletion(), logError()
└── Query: getHistory(N), getEntriesFor(id)
```

## Procedure

### 1. Define Entry and Log Types

```typescript
interface LogEntry {
  taskId: number;       // Correlation ID
  agent: string;         // Actor name
  runId: string;         // Unique run identifier
  status: "dispatched" | "running" | "failed" | "completed";
  startedAt: string;     // ISO timestamp
  completedAt?: string;
  error?: string;
  outputPath?: string;
  pid?: number;
}

interface LogStore {
  entries: LogEntry[];
}
```

### 2. Implement Atomic Read/Write

```typescript
const LOG_PATH = join(process.cwd(), ".project", "audit-log.json");

function readLog(): LogStore {
  if (!existsSync(LOG_PATH)) return { entries: [] };
  try {
    return JSON.parse(readFileSync(LOG_PATH, "utf-8"));
  } catch {
    return { entries: [] };  // Corrupt file → fresh start
  }
}

function writeLog(log: LogStore): void {
  mkdirSync(dirname(LOG_PATH), { recursive: true });
  const tempPath = LOG_PATH + ".tmp";
  writeFileSync(tempPath, JSON.stringify(log, null, 2) + "\n", "utf-8");
  renameSync(tempPath, LOG_PATH);  // Atomic on same filesystem
}
```

**Why tmp → rename?** `writeFileSync` is not atomic — if the process crashes mid-write, the log file is truncated/corrupt. `renameSync` is atomic on most filesystems (ext4, APFS, NTFS).

### 3. Implement Mutation Functions

```typescript
function logEntry(data: Omit<LogEntry, "startedAt">): void {
  const log = readLog();
  log.entries.push({ ...data, startedAt: new Date().toISOString() });
  writeLog(log);
}

function logHeartbeat(taskId: number, runId: string): void {
  // Update matching entry from "dispatched" to "running"
  const log = readLog();
  const entry = log.entries.find(e => e.taskId === taskId && e.runId === runId);
  if (entry && entry.status === "dispatched") entry.status = "running";
  writeLog(log);
}

function logCompletion(taskId: number, runId: string, status: "completed" | "failed", error?: string): void {
  const log = readLog();
  const entry = log.entries.find(e => e.taskId === taskId && e.runId === runId);
  if (entry) {
    entry.status = status;
    entry.completedAt = new Date().toISOString();
    if (error) entry.error = error;
  }
  writeLog(log);
}
```

### 4. Implement Query Helpers

```typescript
function getHistory(limit = 20): LogEntry[] {
  return readLog().entries.slice(-limit).reverse();
}

function getEntriesFor(taskId: number): LogEntry[] {
  return readLog().entries.filter(e => e.taskId === taskId).reverse();
}
```

### 5. Implement Format Helper

```typescript
function formatHistory(limit = 20): string {
  const entries = getHistory(limit);
  if (entries.length === 0) return "No entries yet.";

  const lines: string[] = ["# Audit Log", ""];
  for (const entry of entries) {
    const icon = entry.status === "completed" ? "✅"
      : entry.status === "failed" ? "❌"
      : entry.status === "running" ? "🔄"
      : "📤";
    const duration = entry.completedAt
      ? ` (${Math.round((new Date(entry.completedAt).getTime() - new Date(entry.startedAt).getTime()) / 1000)}s)`
      : "";
    lines.push(`${icon} #${entry.taskId} → ${entry.agent} [${entry.status}]${duration}`);
    if (entry.error) lines.push(`   ⚠ ${entry.error}`);
  }
  return lines.join("\n");
}
```

## Pitfalls

1. **Race conditions** — `readLog()` → mutate → `writeLog()` is not safe across processes. For single-process Node.js it's fine. For multi-process, use a proper lock or append-only approach.
2. **Corrupt JSON on crash** — The catch in `readLog()` returns `{ entries: [] }`, silently losing data. Consider backing up to `.json.bak` before writes.
3. **Large log files** — Every mutation reads and rewrites the entire file. For very high-volume logs, switch to append-only NDJSON (newline-delimited JSON).
4. **renameSync across filesystems** — `renameSync` is only atomic when source and target are on the same filesystem. If `LOG_PATH + ".tmp"` resolves to a different device (e.g., tmpfs vs disk), use `copyFileSync` + `unlinkSync` instead.

## Verification

- [ ] `readLog()` returns `{ entries: [] }` when file doesn't exist
- [ ] `readLog()` handles corrupt JSON gracefully (returns empty)
- [ ] `logEntry(entry)` creates entry with `startedAt` ISO timestamp
- [ ] Temp file (`*.tmp`) is cleaned up after successful write (only `.json` remains)
- [ ] `renameSync` atomicity: kill the process mid-write and verify the existing log is intact
- [ ] `getHistory(N)` returns last N entries in reverse chronological order
- [ ] `formatHistory()` handles empty log gracefully