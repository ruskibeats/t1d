---
name: "relative-time-formatter"
description: "Build a tiered relative time formatter for UI activity timestamps. Formats recent items as relative (\"just now\", \"5m ago\", \"2h ago\"), today items as absolute time (\"11:48\"), and older items as short date (\"05-20\"). Use when displaying timestamps in terminal UIs, boards, dashboards, or activity logs where absolute dates are less useful than recency cues."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Relative Time Formatter

## When to Use

You need to display timestamps in a compact UI (terminal board, activity feed, dashboard, log viewer) where absolute dates are less useful than recency cues. Instead of "2026-05-21T10:30:00Z", show "just now", "5m ago", "2h ago", "11:48" (today), or "05-20" (older).

Use when:
- Building a terminal UI board or dashboard with a "Last activity" column
- Displaying recent task activity, dispatch history, or event logs
- Showing when a background process last checked in
- Any context where the user needs to scan recency at a glance

Do NOT use when:
- You need precise timestamps for audit trails (keep the raw ISO timestamp and add formatter separately)
- Displaying dates more than ~6 months old — use "2026-05-21" format instead of "05-21"

## Procedure

### 1. Get the latest activity date from a task/entity

```typescript
function getLatestActivity(task: Task): Date | undefined {
  const dates: Date[] = [];
  if (task.updatedAt) dates.push(new Date(task.updatedAt));
  if (task.createdAt) dates.push(new Date(task.createdAt));
  if (task.metadata?.lastHeartbeat) dates.push(new Date(task.metadata.lastHeartbeat));
  if (task.metadata?.dispatchedAt) dates.push(new Date(task.metadata.dispatchedAt));

  if (dates.length === 0) return undefined;
  dates.sort((a, b) => b.getTime() - a.getTime());
  return dates[0];
}
```

**Key decision**: Sort descending and take the first (most recent). This gives the user the best recency cue — what happened most recently.

### 2. Compute the tiered format

```typescript
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);

  // Tier 1: Very recent — relative seconds
  if (diffMins < 1) return "just now";

  // Tier 2: Within the hour — relative minutes
  if (diffMins < 60) return `${diffMins}m ago`;

  // Tier 3: Within 24 hours — relative hours
  if (diffHours < 24) return `${diffHours}h ago`;

  // Tier 4: Today — absolute time (no date)
  if (date.toDateString() === now.toDateString()) {
    const h = String(date.getHours()).padStart(2, "0");
    const m = String(date.getMinutes()).padStart(2, "0");
    return `${h}:${m}`;
  }

  // Tier 5: Yesterday or older — short date
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${month}-${day}`;
}
```

**Why these tiers**:

| Tier | Range | Format | Rationale |
|------|-------|--------|-----------|
| 1 | <1 min | "just now" | Instant feedback, no number needed |
| 2 | 1-59 min | "Xm ago" | Precise enough for recent activity |
| 3 | 1-23h | "Xh ago" | Good enough for "this morning/afternoon" |
| 4 | Today | "HH:MM" | Still today, user knows the date |
| 5 | Older | "MM-DD" | Compact, avoids year clutter |

### 3. Integrate into the UI rendering pipeline

```typescript
// In your board model / view model transformation:
function toViewModel(task: Task): ViewModel {
  return {
    id: task.id,
    item: task.item,
    owner: task.assigned ?? task.owner ?? "",
    lastRan: formatRelativeTime(getLatestActivity(task) ?? new Date()),
    status: task.status,
  };
}
```

### 4. Handle edge cases

```typescript
function formatTaskLastRan(task: Task): string {
  const date = getLatestActivity(task);
  if (!date) return "-";  // No activity → placeholder

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);

  // Future dates (clock skew, or created "in the future")
  if (diffMs < 0) return "just now";  // Treat as instant

  // Older than 100 days → show full date to avoid ambiguity
  if (diffHours >= 2400) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  // Normal tiered logic...
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (date.toDateString() === now.toDateString()) {
    return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  }
  return `${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
```

## Design Variants

### Seconds-level precision
```typescript
if (diffSeconds < 60) return `${diffSeconds}s ago`;
```
Use when displaying sub-minute heartbeat or polling activity. Adds precision but adds visual noise — omit unless timing is critical.

### "Yesterday" tier
```typescript
const yesterday = new Date(now);
yesterday.setDate(yesterday.getDate() - 1);
if (date.toDateString() === yesterday.toDateString()) return "yesterday";
```
Insert between Tier 4 and 5 if your UI has space for a word label. Good for task boards where "yesterday" is a meaningful recency signal.

### Absolute time fallback
```typescript
if (diffHours >= 48) {
  return `${date.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
}
```
Use "Apr 21", "May 20" format for medium-old items (2-30 days) instead of "04-21". More readable but longer. Trade-off between compactness and readability.

## Pitfalls

### Timezone skew
- `Date()` uses the local timezone of the system running the code. If the server is UTC but the user is in EST, "just now" could be 5 hours off.
- **Mitigation**: Store all timestamps as UTC (ISO strings), convert to user timezone at render time. For terminal UIs where timezone is known (local machine), this isn't an issue.

### Clock skew from timestamps
- Task `createdAt` may be 2 hours ago even if the task was just assigned.
- **Mitigation**: Use `updatedAt` as the primary source, not `createdAt`. Add domain-specific timestamps (heartbeat, dispatchedAt) for more precise recency.

### Future dates
- A task with `dispatchedAt` set to a future time (e.g., scheduled dispatch) would show "in 2 hours" or show as an elapsed negative.
- **Mitigation**: Treat dates in the future as `"just now"` — it's the most recent activity even if it hasn't technically happened yet.

### "just now" ambiguity
- Multiple items all showing "just now" provides no ordering information.
- **Mitigation**: Add a secondary sort by the actual Date value for ties. This way items that are "just now" are still ordered correctly.

## Verification

```typescript
function testFormatRelativeTime() {
  // Test Tier 1: <1 minute
  assert(formatRelativeTime(new Date()) === "just now");

  // Test Tier 2: Within the hour
  const fiveMinAgo = new Date(Date.now() - 5 * 60000);
  assert(formatRelativeTime(fiveMinAgo) === "5m ago");

  // Test Tier 3: Within 24 hours
  const twoHoursAgo = new Date(Date.now() - 2 * 3600000);
  assert(formatRelativeTime(twoHoursAgo) === "2h ago");

  // Test Tier 4: Today (absolute time)
  const today = new Date();
  today.setHours(11, 48, 0, 0);
  assert(formatRelativeTime(today) === "11:48");

  // Test Tier 5: Older (short date)
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  yesterday.setHours(10, 0, 0, 0);
  // Should show MM-DD format
  const result = formatRelativeTime(yesterday);
  assert(result.match(/^\d{2}-\d{2}$/));

  // Test no activity
  assert(formatTaskLastRan({}) === "-");
}
```