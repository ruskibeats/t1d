# T1D Companion — Sprint Plan

**Created:** 2026-05-18  
**Current state:** 297 tests passing, 18 frontend pages, 25 API routers, 16 domain tables  
**Goal:** Consolidate remaining work into clear, prioritized sprints

---

## Current State Snapshot

| Area | Status | Notes |
|------|--------|-------|
| **Backend core** | ✅ ~95% | All 25 routers wired, agents coordinated, 297 tests passing |
| **Frontend pages** | ✅ ~90% | 18 pages built (Dashboard, Glucose, Food, Exercise, Sleep, Events, Patterns, Chat, Settings, Fasting, Measurements, Mood, Water, Vitals, Activity, HealthMetrics, Login, ExerciseLog) |
| **Test coverage** | ✅ ~85% | 297 tests across 29 test files; missing: dual-write, some provider mocks |
| **Data ingestion** | ⚠️ ~70% | Dexcom/Nightscout services exist, food providers wired; Garmin webhook incomplete |
| **Safety** | ✅ ~90% | Pre-LLM safety works; post-LLM validation not yet added |
| **Deployment** | ⚠️ ~60% | Docker compose exists; no CI/CD, no rate limiting, demo login still hardcoded |
| **UI/UX polish** | ⚠️ ~50% | Functional but needs the consolidated screen architecture (Hoot & Holla, Coach, Memory, etc.) |

---

## Sprint 1: Safety Lockdown + Post-LLM Validation

**Goal:** Make the conversational path clinically safer. Highest priority — this is a medical-adjacent app.

- [ ] **S1-01: Post-LLM safety validation**
  - **Files:** `app/agents/coordinator.py`, `app/api/chat.py`
  - **What:** After `ConversationAgent` produces a response, run it through `SafetyScaffold.validate()`. If unsafe (dosing advice, treatment changes), replace with safe educational fallback + disclaimer.
  - **Acceptance:** Mocked LLM returning "You should take 5 units" → response is blocked/replaced. Safe educational response passes through.
  - **Depends on:** Nothing

- [ ] **S1-02: Deduplicate SafetyAgent logic**
  - **Files:** `app/agents/coordinator.py`
  - **What:** Make `SafetyAgent.handle()` delegate to `SafetyScaffold.validate()` instead of maintaining a separate keyword dictionary.
  - **Acceptance:** No duplicate keyword lists. Single source of truth in `SafetyScaffold`.
  - **Depends on:** S1-01

- [ ] **S1-03: Safety-focused chat tests**
  - **Files:** `tests/test_chat_pipeline.py`
  - **What:** Add tests: dosing advice blocked, treatment-change advice blocked, emergency input short-circuits before LLM, safe response passes.
  - **Acceptance:** 4+ new tests pass. No dosing advice can escape the pipeline.
  - **Depends on:** S1-01, S1-02

**Sprint 1 Acceptance:** Post-LLM safety blocks unsafe content. SafetyAgent delegates to SafetyScaffold. 301+ total tests.

---

## Sprint 2: Frontend Screen Consolidation

**Goal:** Implement the consolidated screen architecture from the UX analysis. Merge duplicate screens, add missing ones.

- [ ] **S2-01: Merge chat screens → Hoot & Holla**
  - **Files:** `frontend/src/pages/Chat.tsx` (rename to `HootHolla.tsx`)
  - **What:** Merge "Talk to Hoot & Holla", "Ask Companion", "AI Advice & Chat" into one screen. Add mic button, camera button, barcode action, prompt chips.
  - **Acceptance:** Single chat screen with all input modes. Prompt chips: "Why am I high right now?", "I'm about to eat", "What happened last time?"
  - **Depends on:** Nothing

- [ ] **S2-02: Merge meal screens → Meal Review flow**
  - **Files:** `frontend/src/pages/FoodLog.tsx`
  - **What:** Consolidate food logging into: Meal Capture → Analysing Meal → Review Meal → Meal Review (with memory of past similar meals).
  - **Acceptance:** 4-step meal flow. "Last time you logged a meal like this, you went high about 3 hours later."
  - **Depends on:** Nothing

- [ ] **S2-03: Merge pattern screens → Patterns**
  - **Files:** `frontend/src/pages/Patterns.tsx`
  - **What:** Collapse all pattern variants into one card-led screen with light grading (Good / Worth watching / Needs attention).
  - **Acceptance:** Pattern cards with plain-English copy. No abstract scores.
  - **Depends on:** Nothing

- [ ] **S2-04: Add Coach page**
  - **Files:** New `frontend/src/pages/Coach.tsx`
  - **What:** New dedicated progress page. "10 days of steadier mornings", "Evening highs improved this week". Gentle gamification, no childish rewards.
  - **Acceptance:** Coach tab in nav. Shows progress streaks and gentle achievements.
  - **Depends on:** Nothing

- [ ] **S2-05: Add Memory page**
  - **Files:** New `frontend/src/pages/Memory.tsx`
  - **What:** Saved observations, stored questions, clinic notes, memorable events. Voice note support.
  - **Acceptance:** Memory tab. Can save pattern observations as notes. Voice note button.
  - **Depends on:** Nothing

- [ ] **S2-06: Add Discuss page**
  - **Files:** New `frontend/src/pages/Discuss.tsx`
  - **What:** "Talk to mummy about this", "Bring to your diabetes review", "Mark for doctor discussion".
  - **Acceptance:** Discuss tab. Actions for sharing patterns with caregivers/clinicians.
  - **Depends on:** Nothing

- [ ] **S2-07: Update navigation + routing**
  - **Files:** `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`
  - **What:** Update routes and sidebar nav to match new screen structure. Remove old duplicate routes.
  - **Acceptance:** Clean nav: Home, Hoot & Holla, Meal Review, Patterns, Coach, Memory, Discuss.
  - **Depends on:** S2-01 through S2-06

- [ ] **S2-08: Copy pass — plain English everywhere**
  - **Files:** All frontend pages
  - **What:** Replace marketing language with plain observations. Cut "calm precision", "optimal state", "humanized health advice". Use "may be", "worth reviewing".
  - **Acceptance:** No marketing fluff. All copy is observational and calm.
  - **Depends on:** S2-07

**Sprint 2 Acceptance:** 13 core screens. Clean nav. Plain-English copy throughout. Coach, Memory, Discuss pages live.

---

## Sprint 3: Security + Deployment Hardening

**Goal:** Production-ready security and infrastructure.

- [ ] **S3-01: Add rate limiting**
  - **Files:** `app/main.py`, `app/api/auth.py`, `app/api/chat.py`
  - **What:** Install `slowapi`. Rate limit: login 5/min, register 3/min, chat 30/min per user.
  - **Acceptance:** >5 login attempts/minute returns 429 with retry-after header.
  - **Depends on:** Nothing

- [ ] **S3-02: Remove hardcoded demo login**
  - **Files:** `frontend/src/contexts/AuthContext.tsx`, `frontend/src/pages/Login.tsx`
  - **What:** Replace hardcoded `demo@t1d.com / demo123` with env-var gated demo mode (`VITE_ENABLE_DEMO=true`).
  - **Acceptance:** Demo button only appears when `VITE_ENABLE_DEMO=true`.
  - **Depends on:** Nothing

- [ ] **S3-03: Dual-write verification tests**
  - **Files:** `tests/test_dual_write.py`
  - **What:** Verify domain creates also produce HealthMetric rows (exercise → EXERCISE_MINUTES, food → CALORIES, sleep → SLEEP_HOURS).
  - **Acceptance:** 3+ tests pass. `health_metrics` table populated on domain creates.
  - **Depends on:** Nothing

- [ ] **S3-04: API smoke test script**
  - **Files:** `scripts/smoke_test.py`
  - **What:** Python script that calls every router once (GET list, POST minimal payload, GET created, DELETE).
  - **Acceptance:** 25/25 endpoints respond with 2xx or expected 4xx.
  - **Depends on:** Nothing

- [ ] **S3-05: Demo data seeder**
  - **Files:** `scripts/seed_demo.py`
  - **What:** Insert realistic multi-day data across all 16 domains with cross-domain correlations.
  - **Acceptance:** After seeding, every frontend page shows real-looking data with visible patterns.
  - **Depends on:** Nothing

- [ ] **S3-06: Production Docker compose**
  - **Files:** `docker-compose.prod.yml`
  - **What:** PostgreSQL 16 service + backend + frontend. Alembic runs on startup.
  - **Acceptance:** `docker compose -f docker-compose.prod.yml up` starts everything.
  - **Depends on:** Nothing

**Sprint 3 Acceptance:** Rate limiting active. Demo login env-gated. Smoke tests pass. Demo data seeder works. Production Docker ready.

---

## Sprint 4: Code Quality + Provider Showcase

**Goal:** Polish and differentiator features.

- [ ] **S4-01: Service method naming consistency**
  - **Files:** All domain services + API routers
  - **What:** Standardize on `create()` / `list()` / `get()` / `delete()` across all 16 domains.
  - **Acceptance:** All domain services use same naming. Tests still pass.
  - **Depends on:** Nothing

- [ ] **S4-02: Add missing `__init__.py` files**
  - **Files:** `app/heart/__init__.py`, `app/blood_pressure/__init__.py`, etc.
  - **What:** All domain packages have `__init__.py`.
  - **Acceptance:** All 16 domain packages importable.
  - **Depends on:** Nothing

- [ ] **S4-03: Garmin webhook end-to-end**
  - **Files:** `app/api/` (garmin route), activity/sleep services
  - **What:** Implement Garmin webhook → parse push data → write to activity_entries/sleep_entries → write to health_metrics.
  - **Acceptance:** `curl POST /api/v1/garmin/webhook` with realistic payload creates entries visible on Activity page.
  - **Depends on:** Nothing

- [ ] **S4-04: Connected devices UI**
  - **Files:** `frontend/src/pages/Settings.tsx`
  - **What:** "Connected devices" section showing provider status. Unimplemented providers labeled "coming soon".
  - **Acceptance:** Settings shows Garmin connected/disconnected. Fitbit/Polar/Strava/Withings show "coming soon".
  - **Depends on:** S4-03

- [ ] **S4-05: Warning cleanup**
  - **Files:** Various (Pydantic V2 `class Config` → `model_config`, SQLAlchemy deprecations, `datetime.utcnow()`)
  - **What:** Reduce warning count by 50%+.
  - **Acceptance:** Full test suite passes. Warning count reduced materially.
  - **Depends on:** Nothing

**Sprint 4 Acceptance:** Consistent naming. Garmin ingestion working. Connected devices UI. Warnings cleaned.

---

## Sprint 5: CI/CD + Launch Prep

**Goal:** Automated testing and production launch readiness.

- [ ] **S5-01: GitHub Actions CI pipeline**
  - **Files:** `.github/workflows/ci.yml`
  - **What:** `pytest` + `tsc --noEmit` + `alembic check` on push/PR.
  - **Acceptance:** CI runs on every push. Fails on test breakage.
  - **Depends on:** All prior sprints

- [ ] **S5-02: Health endpoint metrics**
  - **Files:** `app/main.py` or `app/api/health.py`
  - **What:** `/health` returns connected services status (DB reachable, LLM provider reachable).
  - **Acceptance:** `GET /health` returns JSON with service statuses.
  - **Depends on:** Nothing

- [ ] **S5-03: Database backup script**
  - **Files:** `scripts/backup.sh`
  - **What:** `pg_dump` backup script for PostgreSQL.
  - **Acceptance:** Script runs, produces valid backup file.
  - **Depends on:** Nothing

- [ ] **S5-04: Production deployment docs**
  - **Files:** `DEPLOYMENT.md`
  - **What:** Document production deployment steps end-to-end.
  - **Acceptance:** A new developer can deploy from scratch using only this doc.
  - **Depends on:** S3-06

**Sprint 5 Acceptance:** CI running. Health endpoint live. Backup script works. Deployment documented.

---

## Execution Order & Dependencies

```
Sprint 1 (Safety) ────── NONE — do first, highest priority
Sprint 2 (Frontend) ──── NONE — can run parallel with Sprint 1
Sprint 3 (Security) ──── NONE — can run parallel with Sprints 1-2
Sprint 4 (Quality) ───── NONE — can run after or parallel with Sprint 3
Sprint 5 (CI/CD) ─────── AFTER Sprints 1-4 (needs everything passing)
```

**Recommended approach:** Run Sprints 1 + 2 in parallel (safety backend + frontend UX), then Sprint 3, then Sprint 4, then Sprint 5.

---

## Plan Summary

| Sprint | Tasks | Focus | Est. Effort |
|--------|-------|-------|-------------|
| Sprint 1 | 3 | Post-LLM safety + dedup | 2-3 hrs |
| Sprint 2 | 7 | Screen consolidation + new pages | 4-6 hrs |
| Sprint 3 | 6 | Security + deployment hardening | 3-4 hrs |
| Sprint 4 | 5 | Code quality + Garmin provider | 3-4 hrs |
| Sprint 5 | 4 | CI/CD + launch prep | 2-3 hrs |
| **Total** | **25** | | **14-20 hrs** |

---

## Acceptance Criteria (All Sprints Complete)

- [ ] 301+ tests passing (297 now + 4+ new safety tests)
- [ ] Post-LLM safety blocks unsafe assistant content
- [ ] 13 core frontend screens with clean nav
- [ ] Coach, Memory, Discuss pages live
- [ ] Plain-English copy throughout (no marketing fluff)
- [ ] Rate limiting active on auth + chat
- [ ] Demo login env-gated
- [ ] Dual-write verified
- [ ] Garmin webhook end-to-end working
- [ ] Production Docker compose working
- [ ] CI pipeline running
- [ ] Deployment documented
