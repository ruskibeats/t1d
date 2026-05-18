# Frontend Bugs

## Category 1: API URL Mismatches (Frontend calls wrong endpoints)

### F1.1 Login page calls non-existent `/auth/login-with-email`
**File:** `src/contexts/AuthContext.tsx` (line 42)
```ts
await axios.post('/auth/login-with-email', { email, password })
```
**Backend actual route:** `POST /auth/login` (form-encoded with `username` and `password`, OAuth2 style)
**Impact:** Login always fails on the real backend. Falls through to the demo account fallback (line 56-62).
**Fix:** Change to `POST /auth/login` with `FormData` containing `username={email}&password={password}` — or better, create a matching backend endpoint. The backend does have `/auth/login-with-email` (line 115 of `app/api/auth.py`) which accepts JSON `{email, password}` — so this is actually fine!

### F1.2 Glucose hook calls wrong URL for stats
**File:** `src/hooks/useGlucose.ts` (line 87)
```ts
await axios.get(`${API_BASE}/glucose/stats/?${params}`)
```
**Backend actual route:** `GET /api/v1/glucose/stats/` — this is correct.

### F1.3 Glucose hook `fetchReadings` calls wrong URL
**File:** `src/hooks/useGlucose.ts` (line 78)
```ts
await axios.get(`${API_BASE}/glucose/?${params}`)
```
**Backend actual route:** `GET /api/v1/glucose/` — but the backend accepts `?start_time=`, `?end_time=` as query parameters. This should work.

### F1.4 Events hook passes `?limit=` to backend
**File:** `src/hooks/useEvents.ts` (line 26)
```ts
const response = await axios.get(`/api/v1/events/?limit=${limit}`)
```
**Backend actual route:** `GET /api/v1/events/` — has `skip=0, limit=100` default params. This is correct.

### F1.5 Exercise hook passes `?start=` and `?end=` params
**File:** `src/hooks/useExercise.ts` (line 53)
```ts
const response = await axios.get(`/api/v1/exercise?${params.toString()}`)
```
**Backend route:** not clearly defined for exercise — exercise uses APIRouter but no GET endpoints were found in the grep. **This will return 404.**
**Fix:** Check if exercise router has GET list endpoint.

### F1.6 Food hook passes wrong URL for create
**File:** `src/hooks/useFood.ts` (line 86)
```ts
const response = await axios.get(`/api/v1/food/search?q=${encodeURIComponent(query)}`)
```
**Backend route:** `GET /api/v1/food/search` — need to verify this exists.

### F1.7 Food hook creates entries at wrong URL
**File:** `src/hooks/useFood.ts` (line 111)
```ts
const response = await axios.post('/api/v1/food/entries', data)
```
**Backend route:** Need to verify food router has `POST /entries`. Food router is imported as `food.route` with prefix `/api/v1`.

---

## Category 2: Broken Buttons / Non-functional Interactions

### F2.1 QuickLog buttons do nothing
**File:** `src/components/dashboard/QuickLog.tsx` (line 40)
```ts
onClick={() => console.info(`Quick log ${action.label}`)}
```
**Impact:** All 4 quick-log buttons (Glucose, Meal, Insulin, Exercise) just log to console. They should open a form or navigate to the relevant page.

### F2.2 "Log event" button on Dashboard does nothing
**File:** `src/pages/Dashboard.tsx` (line 53):
```tsx
<Button size="lg" className="..."><Plus className="h-4 w-4" /> Log event</Button>
```
**Impact:** No `onClick` handler, no navigation.

### F2.3 "Ask AI" button on Dashboard does nothing
**File:** `src/pages/Dashboard.tsx` (line 57):
```tsx
<Button size="lg" variant="outline" className="..."><Brain className="h-4 w-4" /> Ask AI</Button>
```
**Impact:** No `onClick` handler, no navigation to `/chat`.

### F2.4 "Add reading" button on Dashboard Glucose trace card does nothing
**File:** `src/pages/Dashboard.tsx` (line 86):
```tsx
<Button variant="outline"><Plus className="h-4 w-4" /> Add reading</Button>
```
**Impact:** No `onClick` handler, no navigation.

### F2.5 "Add reading" button on Glucose page does nothing
**File:** `src/pages/Glucose.tsx` (line 32):
```tsx
<Button><PlusIcon className="h-4 w-4" /> Add reading</Button>
```
**Impact:** No `onClick` handler.

### F2.6 "New event" button on Events page does nothing
**File:** `src/pages/Events.tsx` (line 39):
```tsx
<Button><PlusIcon className="h-4 w-4" /> New event</Button>
```
**Impact:** No `onClick` handler.

### F2.7 "Save changes" button on Settings/Profile does nothing
**File:** `src/pages/Settings.tsx` (line 39):
```tsx
<Button>Save changes</Button>
```
**Impact:** No `onClick` handler. Profile data is not persisted anywhere.

### F2.8 "Week view" button on Events page does nothing
**File:** `src/pages/Events.tsx` (line 101):
```tsx
<Button variant="outline" size="sm">Week view</Button>
```
**Impact:** No `onClick` handler.

### F2.9 "Log first event" button on Dashboard/RecentEvents does nothing
**File:** `src/components/dashboard/RecentEvents.tsx` (line 41):
```tsx
<Button variant="outline" size="sm" className="mt-4">Log first event</Button>
```
**Impact:** No `onClick` handler.

### F2.10 "Connect Dexcom" and "Connect Nightscout" buttons do nothing
**File:** `src/pages/Settings.tsx` (line 58):
```tsx
<Button variant="outline">Connect Dexcom</Button>
<Button variant="outline">Connect Nightscout</Button>
```
**Impact:** No `onClick` handlers.

### F2.11 "Delete account" button does nothing
**File:** `src/pages/Settings.tsx` (line 73):
```tsx
<Button variant="outline" className="...">Delete account</Button>
```
**Impact:** No `onClick` handler. No confirmation dialog.

---

## Category 3: Duplicate / Orphaned Code

### F3.1 Two `useGlucose` hooks — one stale, one active
**Files:**
- `src/hooks/useGlucose.ts` — **active, used by `Dashboard.tsx`** (imports from `@/hooks/useGlucose`)
- `src/contexts/GlucoseContext.tsx` — **orphaned, no component imports it**

**Impact:** The `Dashboard.tsx` imports `useGlucose` from the hook, not the context. `GlucoseContext.tsx` has its own `fetchReadings` (without time range), `addReading`, and `useEffect`. The context is never provided to any component tree. It should be removed or consolidated.

### F3.2 Dashboard imports both `useGlucose` hook AND `useEvents` hook
**File:** `src/pages/Dashboard.tsx` (lines 15-16)
```tsx
import { useGlucose } from '@/hooks/useGlucose'
import { useEvents } from '@/hooks/useEvents'
```
The Dashboard's `useGlucose` returns `{ readings, stats, demoMode, fetchReadings }` but the original hook `useGlucose()` returns `{ readings, stats, loading, demoMode, fetchReadings, addReading, getStats }`. The Dashboard destructures `demoMode` which exists in the hook — this is fine but the interface mismatch could cause issues.

---

## Category 4: Type & Interface Issues

### F4.1 GlucoseReading type doesn't have `reading_type` field
**File:** `src/types/index.ts` and `src/hooks/useGlucose.ts` (line 98)
```ts
addReading(data: Omit<GlucoseReading, 'id' | 'timestamp'>)
```
But the hook's `addReading` adds:
```ts
reading_type: 'sensor',
```
The `GlucoseReading` interface does not have a `reading_type` field.

**Impact:** TypeScript allows it because `reading_type` is added via object spread. But it technically doesn't match the type definition.

### F4.2 Dashboard uses `useGlucose()` returning different shape
**File:** `src/pages/Dashboard.tsx` (line 28):
```ts
const { readings, stats, demoMode, fetchReadings } = useGlucose()
```
The actual hook `useGlucose` returns `readings, stats, loading, demoMode, fetchReadings, addReading, getStats`. The Dashboard destructures a subset, which works, but `demoMode` is consumed while `loading` is not.

---

## Category 5: Data Handling Issues

### F5.1 Stale Context — `GlucoseContext` never used
**File:** `src/contexts/GlucoseContext.tsx`
The `GlucoseProvider` component is never imported or used in `App.tsx`. The context's internal state is initialized with empty arrays, and its `fetchReadings()` is called in `useEffect` but — since the provider is never mounted — it never runs.

### F5.2 Dashboard stats usage with optional chaining
**File:** `src/pages/Dashboard.tsx` (lines 66-68):
```tsx
<StatCard title="Time in range" value={stats?.time_in_range ? `${stats.time_in_range.percentage.toFixed(0)}%` : '--'} .../>
```
`stats` is typed as `NormalizedStats` which guarantees `time_in_range` exists. Optional chaining masks real issues.

### F5.3 Dashboard uses `readings[0].glucose_value` and `readings[1].glucose_value` without null check
**File:** `src/pages/Dashboard.tsx` (line 35-36):
```ts
const trend = readings.length >= 2 ? readings[0].glucose_value - readings[1].glucose_value : 0
```
Line 38: `const status = latestReading?.glucose_value < 70 ? ...` — the `?.` on `glucose_value` is fine but `status` will be `false` when `latestReading` is undefined (i.e., `undefined < 70` is `false`, `undefined > 180` is `false`, so `status = 'in range'`). That's a logical bug — no readings means `status` incorrectly shows "in range".

### F5.4 Pattern page uses `new Date(event.date)` on date string
**File:** `src/pages/Patterns.tsx` (line 143):
```tsx
{new Date(event.date).toDateString()}
```
In `demoOvernight`, `event.date` is already an ISO string from `new Date(...).toISOString()`. `new Date(isoString).toDateString()` works but the demo data's `date` field uses `new Date(now - 2 days).toISOString()` which includes a time component — parsing it back to a Date gives the wrong date if the time crosses midnight boundary. This is a timezone display issue.

---

## Category 6: Missing Dependencies / Build Risk

### F6.1 Missing `@emotion/react` JSX pragma consistency
**Files:** `src/lib/demoData.ts` — does NOT have `/** @jsxImportSource @emotion/react */` pragma (and doesn't need it since it has no JSX). All other `.tsx` files DO have it. This is fine.

### F6.2 Tailwind classes used but risky
Many files use raw OKLCH colors with `text-[oklch(...)]`, `bg-[oklch(...)]`, etc. This is valid in Tailwind v3.3+ with arbitrary values. Should work as long as Tailwind is configured properly.

### F6.3 No error boundaries
No component uses React error boundaries. If any page throws during render, the entire app crashes.

---

## Category 7: Security Issues

### F7.1 Hardcoded demo credentials
**File:** `src/contexts/AuthContext.tsx` (line 56):
```ts
if (email === 'demo@t1d.com' && password === 'demo123') {
```
Hardcoded credentials in the frontend source code. Low risk since it's a demo app, but notable.

### F7.2 Demo fallback creates fake JWT tokens
**File:** `src/contexts/AuthContext.tsx` (line 57):
```ts
const demoToken = `demo-${Date.now()}`
```
The demo token prefix `demo-` is checked across all hooks to decide whether to use demo data or call the real API. This means anyone who knows `demo-` can access demo data. Not a real security concern since there's no real data.

---

## Category 8: Console.log / Debug Leftovers

### F8.1 Widespread `console.info` for demo fallback logging
**Files:** `src/pages/Patterns.tsx` (line 57), `src/hooks/useFood.ts` (lines 80, 120), `src/hooks/useEvents.ts` (line 27), `src/hooks/useGlucose.ts` (line 82)

These are intentional — they log that demo data is being used when the API is unavailable. Not a bug but should be converted to a silent fallback or use a proper logger in production.

### F8.2 `console.error` in GlucoseContext
**File:** `src/contexts/GlucoseContext.tsx` (lines 31, 43) — orphaned component.

### F8.3 QuickLog buttons log to console
**File:** `src/components/dashboard/QuickLog.tsx` (line 40) — should navigate to forms.

---

## Category 9: Edge Cases

### F9.1 Dashboard `latestReading?.glucose_value` — can produce `false` status
When `latestReading` is `undefined`, `latestReading?.glucose_value < 70` evaluates to `undefined < 70` which is `false`. The ternary then checks `latestReading?.glucose_value > 180` which is also `undefined > 180` → `false`. So `status = 'in range'` even though there are no readings. The UI renders `status` badge as "in range" with green styling, which is misleading.

### F9.2 Pattern page shows `overnight.date` as `Invalid Date` for empty arrays
**File:** `src/pages/Patterns.tsx` — the `map` over `overnight` is inside a conditional that checks `overnight.length === 0`. If `overnight` is non-empty but has missing `date` fields, `new Date(undefined).toDateString()` returns `"Invalid Date"`.

### F9.3 Chat page sends request body with `conversation_id: undefined`
**File:** `src/pages/Chat.tsx` (line 72):
```ts
conversation_id: undefined,
```
FastAPI will include `conversation_id` in serialized JSON as `null`. The chat endpoint should handle `null`/`undefined` conversation IDs gracefully by creating a new conversation.

---

## Summary Table

| Priority | Bug ID | Description | Severity |
|----------|--------|-------------|----------|
| **HIGH** | F2.1–F2.11 | 11 buttons do nothing (no onClick handlers) | User-facing |
| **HIGH** | F3.1 | Orphaned `GlucoseContext` — dead code | Maintainability |
| **MED** | F1.1 | Login URL — falls through to demo | User-facing |
| **MED** | F1.5 | Exercise GET may return 404 | Data loading |
| **MED** | F6.3 | No error boundaries | App stability |
| **LOW** | F4.1/F4.2 | Type mismatches | Type safety |
| **LOW** | F5.3/F9.1 | Edge case when no readings | Edge case |
| **LOW** | F8.1–F8.3 | Console debug logging | Production cleanup |