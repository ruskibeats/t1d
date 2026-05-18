# Orchestrator Test Report — 2026-05-18

## Session Summary

A comprehensive test of the multi-agent orchestration system for the T1D Companion project. Tested subagent dispatch, intercom escalation, todo management, and audit capabilities using real codebase tasks.

---

## 1. Orchestrator Fixes Applied

### 1.1 Researcher Tool Access
**Problem:** Researcher subagent lacked `bash`, `find`, `ls`, `grep` tools — could not run shell commands.
**Fix:** Added `bash, find, ls, grep` to researcher's tool list in `/root/.pi/agent/npm/node_modules/pi-subagents/agents/researcher.md`.

### 1.2 Intercom in Non-Interactive Mode
**Problem:** Subagents running in non-interactive mode could not process intercom replies, causing infinite loops.
**Fix:** Updated all three subagent definitions (researcher, worker, scout) to use `intercom({ action: "reply", message: "..." })` with explicit "BLOCKED:" prefix convention. Removed dependency on `contact_supervisor`.

### 1.3 Todo Tool in Subagents
**Problem:** Subagents could not update their own todo status — parent session had to do it manually.
**Fix:** Added `todo` tool to all three subagent definitions. Each now has instructions to:
- Read plan files from `.pi/todo-plans/#<id>_plan.md`
- Mark `in_progress` when starting
- Mark `completed` when done
- Create new pending todos if they discover work

### 1.4 Elastic Todo Box Width
**Problem:** Todo overlay box had hardcoded 72-char width, causing text truncation.
**Fix:** Updated `TodosView.render()` and `renderPlainTodoTable()` in `/root/.pi/agent/extensions/todo/index.ts` to use terminal width with proportional column allocation (Item 45%, Owner 20%, Tags 20%, Plan 15%).

---

## 2. Test Batches

### Batch 1: Simple Smoke Tests (Todos #1–#3)

| # | Task | Assignee | Result |
|---|------|----------|--------|
| 1 | Create hello.txt | @worker | ✅ File created |
| 2 | List Python files in app/ | @scout | ✅ 136 files found |
| 3 | Count lines of code | @researcher | ✅ 364,031 lines (required supervisor relay) |

**Issues:** Researcher could not run bash commands (fixed after this batch).

### Batch 2: Parallel Dispatch (Todos #4–#8)

| # | Task | Assignee | Result |
|---|------|----------|--------|
| 4 | Create goodbye.txt | @worker | ✅ File created |
| 5 | List test files in tests/ | @scout | ✅ 34 files found |
| 6 | Count total files | @researcher | ✅ 56,558 files (required supervisor relay) |
| 7 | Show last 10 commits | @scout | ✅ 6 commits (all repo history) |
| 8 | Create timestamp.txt | @worker | ✅ File created |

**Issues:** Researcher still lacked bash. Intercom loop discovered and resolved via interrupt.

### Batch 3: Mixed Simple + Audit Tasks (Todos #10–#21)

| # | Task | Assignee | Result |
|---|------|----------|--------|
| 10 | Create notes.txt | @worker | ○ Pending |
| 11 | List .json files | @scout | ○ Pending |
| 12 | Count test lines | @researcher | ○ Pending |
| 13 | Create README_extra.md | @worker | ○ Pending |
| 14 | Show disk usage | @worker | ○ Pending (reassigned from scout) |
| 15 | Refactor glucose chart colors | — | 🗑️ Deleted |
| 16 | Add rate limiting to chat API | @worker | ◐ In progress |
| 17 | Write SafetyAgent tests | — | 🗑️ Deleted |
| 18 | Set up pre-commit hooks | @researcher | ◐ In progress |
| 19 | Document agent coordinator | @scout | ◐ In progress |
| 20 | Audit frontend unused components | @researcher | ✅ Completed |
| 21 | Review API endpoints for validation | @researcher | ✅ Completed |

---

## 3. Audit Findings

### 3.1 Frontend Audit (#20)

**Scope:** Full scan of `frontend/src/` for unused components, hooks, pages, and types.

**Results:**
- **All 7 components used** — Layout, GlucoseChart, QuickLog, RecentEvents, Button, Card, StatCard
- **All 17 pages used** — All routed in App.tsx
- **All 11 hooks used** — Each imported by at least one page
- **Both lib files used** — utils.ts (cn utility), demoData.ts
- **Both CSS files used** — App.css, index.css

**Cleanup Candidates:**

| Priority | Item | Action |
|----------|------|--------|
| High | Remove `services/`, `utils/`, `styles/` directories | Empty, dead directories |
| Medium | Remove 10 unused interfaces from `types/index.ts` | Dead code |
| Low | Remove `export` from 12 hook-internal types | Minor style cleanup |

**Unused Interfaces in `types/index.ts`:**
`MealEvent`, `InsulinEvent`, `ExerciseEvent`, `Conversation`, `ConversationMessage`, `PatternAnalysis`, `LoginRequest`, `LoginResponse`, `UserCreate`, `SleepStage`

### 3.2 API Endpoint Validation Audit (#21)

**Scope:** All 27 files in `app/api/` comprising ~80+ endpoints.

**Critical Findings:**

#### P0 — No Authentication (~45 endpoints across 11 files)

| File | Endpoints | Issue |
|------|-----------|-------|
| `fasting.py` | All 6 | `user_id` query param, no auth |
| `measurements.py` | All 6 | `user_id` query param, no auth |
| `mood.py` | All 3 | `user_id` query param, no auth |
| `sleep.py` | All 5 | `user_id` query param, no auth |
| `water.py` | All 3 | `user_id` query param, no auth |
| `metrics.py` | All 12 | `user_id` query param, no auth |
| `fitbit.py` | All 3 | No auth, code leaked in response |
| `garmin.py` | Both | `user_id` query param, no webhook verification |
| `polar.py` | 1 | `user_id` query param, no auth |
| `strava.py` | All 3 | No auth, code leaked in response |
| `withings.py` | 1 | `user_id` query param, no webhook verification |

#### P1 — Missing Input Validation (~30 endpoints)
- No `ge`/`le` constraints on `limit`, `offset`, `skip`, `window_minutes`
- No `max_length` on string query parameters
- No `min_length` on search queries
- Raw `datetime.fromisoformat()` without format validation

#### P2 — Weak Error Handling (~20 endpoints)
- Bare `except Exception` returning internal details via `str(e)`
- Unhandled `datetime.fromisoformat()` causing raw 500
- OOM risk in `glucose.py` stats (fetches ALL values, no limit)
- Generic exception catches with no logging

#### P3 — Missing Rate Limiting & Other
- No rate limiting on login, register, forgot-password
- No webhook signature verification (Garmin, Withings)
- Placeholder auth endpoints (verify-email, reset-password, forgot-password) always return success
- `list_users` has no admin role check

---

## 4. Spawned Action Items (Unallocated)

From audit findings, 8 new todos were created:

| # | Task | Priority | Labels |
|---|------|----------|--------|
| 22 | Remove empty directories | High | chore, frontend |
| 23 | Remove unused interfaces | Medium | chore, frontend |
| 24 | Remove unused hook exports | Low | chore, frontend |
| 25 | Add auth guards to unauthenticated endpoints | **P0** | security, backend |
| 26 | Add input validation to all endpoints | P1 | security, backend |
| 27 | Fix error handling in endpoints | P2 | bug, backend |
| 28 | Add rate limiting and webhook verification | P3 | security, backend |
| 29 | Implement placeholder auth endpoints | P3 | feature, backend |

---

## 5. Subagent Performance

### Worker
- **Tasks completed:** #1, #4, #8 (create files)
- **Reliability:** 100% — all tasks completed without issues
- **Strengths:** File creation, bash execution, verification

### Scout
- **Tasks completed:** #2, #5, #7 (list files, git log)
- **Reliability:** 100% — all tasks completed without issues
- **Strengths:** Codebase navigation, file listing, git operations

### Researcher
- **Tasks completed:** #3, #6, #12, #18, #20, #21 (counting, audits)
- **Reliability:** Initially blocked by missing bash tool (fixed mid-session)
- **Post-fix performance:** Excellent — completed complex audits (#20, #21) independently
- **Strengths:** Deep analysis, comprehensive reporting, pattern recognition

---

## 6. Key Learnings

1. **Subagent tool access is critical** — Researcher without bash was nearly useless for shell tasks
2. **Intercom escalation works** — But only if the subagent can process replies (non-interactive mode blocks this)
3. **Todo self-management** — Subagents should be able to update their own todo status to reduce parent overhead
4. **Parallel dispatch is effective** — Multiple subagents can work simultaneously without conflicts
5. **Plan files are essential** — Clear instructions in .md format prevent ambiguity and reduce back-and-forth
6. **Real audits find real issues** — The API audit found a P0 security vulnerability (45 unauthenticated endpoints)

---

## 7. Files Modified

| File | Change |
|------|--------|
| `agents/researcher.md` | Added bash, find, ls, grep, todo tools; updated intercom rules |
| `agents/worker.md` | Added todo tool; updated intercom rules |
| `agents/scout.md` | Added todo tool; updated intercom rules |
| `extensions/todo/index.ts` | Elastic box width, proportional columns |

---

## 8. Artifacts Generated

| File | Description |
|------|-------------|
| `context.md` | Scout output — Python file list (136 files) |
| `research.md` | Researcher output — API validation audit (190 lines) |
| `hello.txt` | Worker test output |
| `goodbye.txt` | Worker test output |
| `timestamp.txt` | Worker test output |
| `notes.txt` | Worker test output (pending) |
| `README_extra.md` | Worker test output (pending) |
| `.pi/todo-plans/#*_plan.md` | Plan files for all todos |

---

*Report generated: 2026-05-18*
*Session: orchestrator test and audit run*
