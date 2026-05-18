# T1D Companion — Hardening Plan

**From**: System review dated May 17, 2026  
**Current state**: 258 tests, 14,850 lines Python, 4,110 lines TypeScript, 25 API routers, 16 domain tables  
**Target**: Investor-demo ready → production-hardened

---

## Phase 1: Test Coverage Expansion (HIGH — 7 new domains untested)

### 1.1 Write API tests for 7 new backend domains

Each test file follows `tests/test_api_exercise.py` pattern: create, list, get, delete, invalid data rejection.

- [ ] **1.1.1** `tests/test_heart.py` — 5+ tests
- [ ] **1.1.2** `tests/test_blood_pressure.py` — 5+ tests
- [ ] **1.1.3** `tests/test_activity.py` — 5+ tests
- [ ] **1.1.4** `tests/test_vitals.py` — 5+ tests
- [ ] **1.1.5** `tests/test_body_composition.py` — 5+ tests
- [ ] **1.1.6** `tests/test_lifestyle.py` — 5+ tests
- [ ] **1.1.7** `tests/test_body_battery.py` — 5+ tests

**Acceptance**: pytest passes with 293+ total tests after.

### 1.2 Write dual-write verification tests

- [ ] **1.2.1** `tests/test_dual_write.py` — 3+ tests that verify domain creates also produce HealthMetric rows for at least 3 domains (exercise → EXERCISE_MINUTES, food → CALORIES, sleep → SLEEP_HOURS)

**Acceptance**: Verified that `health_metrics` table is populated when domain entries are created.

### 1.3 Write smoke test for all 25 API routers

- [ ] **1.3.1** `scripts/smoke_test.py` — Python script that calls every router once (GET on list endpoints, POST a minimal valid payload, GET the created resource, DELETE it)

**Acceptance**: 25/25 endpoints respond with 2xx or expected 4xx.

---

## Phase 2: Database Hardening (HIGH — SQLite dev vs PostgreSQL production)

### 2.1 Generate Alembic migration for new domains

- [ ] **2.1.1** Run `alembic revision --autogenerate -m "add_eight_new_domains"` to create migration for heart, blood_pressure, activity, vitals, body_composition, body_battery, lifestyle, environment tables
- [ ] **2.1.2** Verify migration up/down works on a test PostgreSQL instance
- [ ] **2.1.3** Add the 8 new table models to `tests/conftest.py` SQLite fixture (individual table creation with try/except pattern)

**Acceptance**: `alembic upgrade head` creates all 16 domain tables on a fresh PostgreSQL database.

### 2.2 Add PostgreSQL environment configuration

- [ ] **2.2.1** Create `docker-compose.prod.yml` with PostgreSQL 16 service, backend, and frontend
- [ ] **2.2.2** Update `.env.example` with PostgreSQL `DATABASE_URL` example
- [ ] **2.2.3** Add startup check in `app/main.py` that warns if SQLite is detected on a non-development environment

**Acceptance**: `docker compose -f docker-compose.prod.yml up` starts backend + frontend + PostgreSQL, and Alembic runs on startup.

### 2.3 Create demo data seeder

- [ ] **2.3.1** `scripts/seed_demo.py` — Python script that inserts realistic multi-day data across all 16 domains (glucose curve, meals with carbs, exercise, sleep with stages, heart rate, BP, SpO2, weight, steps, mood, water, body battery)
- [ ] **2.3.2** Include cross-domain correlations for compelling demo: high-fat meal → delayed spike, exercise → glucose drop, poor sleep → higher next-day glucose, stress → elevated heart rate

**Acceptance**: After seeding, every frontend page shows real-looking data with visible patterns.

---

## Phase 3: Production Security Hardening (MEDIUM — rate limiting, demo removal)

### 3.1 Enable rate limiting

- [ ] **3.1.1** Install `slowapi` package
- [ ] **3.1.2** Add rate limiting to `/auth/login` (5/minute per IP)
- [ ] **3.1.3** Add rate limiting to `/auth/register` (3/minute per IP)
- [ ] **3.1.4** Add rate limiting to `/api/v1/chat` (30/minute per user)
- [ ] **3.1.5** Remove the TODO comment in `app/api/auth.py:214`

**Acceptance**: More than 5 login attempts/minute returns 429 with retry-after header.

### 3.2 Remove demo login from AuthContext

- [ ] **3.2.1** Remove hardcoded `demo@t1d.com / demo123` credential check from `frontend/src/contexts/AuthContext.tsx`
- [ ] **3.2.2** Replace with env-var gated demo mode: `VITE_ENABLE_DEMO=true` controls whether demo button appears on Login page
- [ ] **3.2.3** Update `frontend/src/pages/Login.tsx` demo button to check `import.meta.env.VITE_ENABLE_DEMO`

**Acceptance**: Demo button only appears when `VITE_ENABLE_DEMO=true`. Normal login flow unchanged.

---

## Phase 4: Code Quality & Consistency (MEDIUM — technical debt)

### 4.1 Add `__init__.py` to new domain packages

- [ ] **4.1.1** Create `app/heart/__init__.py`
- [ ] **4.1.2** Create `app/blood_pressure/__init__.py`
- [ ] **4.1.3** Create `app/activity/__init__.py`
- [ ] **4.1.4** Create `app/vitals/__init__.py`
- [ ] **4.1.5** Create `app/body_composition/__init__.py`
- [ ] **4.1.6** Create `app/lifestyle/__init__.py`
- [ ] **4.1.7** Create `app/body_battery/__init__.py`

**Acceptance**: All domain packages have `__init__.py` (can be empty).

### 4.2 Standardize service method naming

New domains use shorter pattern: `create()` / `list()` / `get()` / `delete()`.
Old domains use longer pattern: `create_entry()` / `list_entries()` / `get_entry()` / `delete_entry()`.

- [ ] **4.2.1** Rename old service methods to match new convention (or vice versa — pick one and apply consistently)
- [ ] **4.2.2** Update all callers in API routers to use new method names

**Acceptance**: All 16 domain services use the same method naming convention. Tests still pass.

### 4.3 Clean up `glycemic_index` type

- [ ] **4.3.1** Decide: both `glycemic_index` and `glycemic_load` should be `Float` (numeric GI values) or make `glycemic_index` a proper enum `("low", "medium", "high")`
- [ ] **4.3.2** Update `app/food/models.py`, `app/food/schemas.py`, and any frontend consumers

**Acceptance**: `glycemic_index` and `glycemic_load` have consistent types.

---

## Phase 5: Ingestion Provider Showcase (MEDIUM — demo differentiator)

- [ ] **5.1** Implement one end-to-end ingestion provider: Garmin webhook → parse push_limits/sleep data → write to activity_entries/sleep_entries → write to health_metrics
- [ ] **5.2** Add a "Connected devices" section to Settings page showing provider status (Garmin connected/disconnected)
- [ ] **5.3** Label unimplemented providers (Fitbit, Polar, Strava, Withings) as "coming soon" in the UI

**Acceptance**: A curl POST to `/api/v1/garmin/webhook` with a realistic Garmin payload creates activity entries visible on the Activity page.

---

## Phase 6: Infrastructure & CI (LOW — post-investor demo)

- [ ] **6.1** Add GitHub Actions CI pipeline: `pytest` + `tsc --noEmit` + `alembic check`
- [ ] **6.2** Add health endpoint metrics: `/health` returns connected services status (DB reachable, LLM provider reachable)
- [ ] **6.3** Add database backup script for PostgreSQL: `scripts/backup.sh` using `pg_dump`
- [ ] **6.4** Document production deployment steps in `DEPLOYMENT.md`

---

## Execution Order & Dependencies

```
Phase 1 (Tests) ────── NONE — independent, parallelizable
Phase 2 (Database) ──── AFTER Phase 1.1 (need models confirmed before migration)
Phase 3 (Security) ──── NONE — independent, parallelizable  
Phase 4 (Quality) ───── NONE — independent, parallelizable
Phase 5 (Providers) ─── AFTER Phase 2 (need migration for provider-specific columns)
Phase 6 (CI) ────────── AFTER Phase 1 (need tests passing in CI)
```

**Recommended sprint order**: Phase 1 + 3 in parallel (tests + security), then Phase 2 + 4 (database + quality), then Phase 5 (provider showcase), then Phase 6 (CI).

---

## Effort Estimates

| Phase | Tasks | Estimated Hours |
|-------|-------|----------------|
| Phase 1: Tests | 9 test files + smoke script | 2-3 |
| Phase 2: Database | Migration + Docker + Seeder | 2-3 |
| Phase 3: Security | Rate limiting + demo removal | 1-2 |
| Phase 4: Quality | __init__.py + naming + GI type | 1-2 |
| Phase 5: Providers | Garmin end-to-end | 2-3 |
| Phase 6: CI | GitHub Actions + backup + docs | 1-2 |
| **Total** | | **9-15 hours** |
