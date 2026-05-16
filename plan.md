# Implementation Plan

## Goal
Turn the high-level build tasks from `.BUILD_TASKS.md` into an ordered, concrete execution plan with exact file paths, dependencies, and acceptance criteria for each task.

---

## Current State Snapshot

| Phase | Status | Notes |
|-------|--------|-------|
| **P0** | ~80% complete | `app/metrics/` domain, schemas, service, API, and Alembic migration exist and are wired into `app/main.py`. Missing: `app/ai/safety.py` (P0-05). |
| **P1** | ~15% complete | `app/food/` models/schemas/service/API exist but no Alembic migration yet; `app/exercise/`, `app/sleep/`, `app/measurements/`, `app/fasting/`, `app/mood/`, `app/water/` do not exist. |
| **P2** | 0% | No ingestion providers beyond Dexcom/Nightscout. |
| **P3** | 0% | No `app/ai/` directory. Agents in `app/agents/coordinator.py` are stubs. |
| **P4** | 0% | No external provider ingestion modules. |
| **P5** | 0% | No food provider integrations. |
| **P6** | ~30% | Frontend has Dashboard, Glucose, Events, Patterns, Chat, Settings, Login. Missing: dedicated Food/Exercise/Sleep pages and unified health-metrics dashboard. |

---

## Tasks

### Phase 0: Schema Foundation (Finish Remaining)

1. **P0-05: `app/ai/safety.py` — SafetyScaffold with condition-specific guardrail builder**
   - **New File:** `app/ai/safety.py`
   - **Changes:**
     - Create `SafetyScaffold` class with `build_guardrails(condition: str, severity: str) -> list[str]`.
     - Include emergency keyword detection (reuse/replace logic currently in `app/services/llm_service.py` `_contains_emergency_keywords`).
     - Add condition-specific rules: `diabetes_emergency` (severe low, DKA), `mental_health_crisis`, `general_medical`.
     - Expose `validate(content: str, context: dict) -> dict` returning `{"is_safe": bool, "safety_level": str, "reasons": list, "requires_escalation": bool}`.
   - **Acceptance:**
     - Import succeeds in `app/ai/__init__.py`.
     - Unit test (to be added in `tests/ai/test_safety.py`) flags `"severe low blood sugar"` as `requires_escalation=True`.
     - Does **not** flag normal glucose questions as unsafe.
   - **Depends on:** Nothing (new module).
   - **Order:** Complete before Phase 3 agents call safety checks.

---

### Phase 1: Domain Packages (Sparky Models → Python)

2. **P1-01: `app/food/` — finalize tables + Alembic migration**
   - **Files:**
     - `app/food/models.py` — already exists (`Food`, `FoodEntry`).
     - `app/food/schemas.py` — already exists.
     - `app/food/service.py` — already exists.
     - `app/api/food.py` — already exists.
     - **New:** `alembic/versions/add_food_tables.py`
   - **Changes:**
     - Write Alembic migration creating `foods` and `food_entries` with all columns from `app/food/models.py`.
     - Add `foods` and `food_entries` relationships to `app/db/models.py` on `User` (currently only `health_metrics` / `health_daily_aggregates` are linked).
     - Add `__init__.py` in `app/food/` if missing.
   - **Acceptance:**
     - `alembic upgrade head` applies successfully.
     - `POST /api/v1/food` and `POST /api/v1/food/entries` persist rows.
   - **Depends on:** P0 schema conventions (use same timestamp/index patterns as `add_health_metrics_and_aggregates.py`).

3. **P1-02: `app/exercise/` — exercise_entries + exercise_entry_sets**
   - **New Files:**
     - `app/exercise/models.py` — `ExerciseEntry` (id, user_id, type, start_time, end_time, duration, calories, heart_rate_avg, source, meta) and `ExerciseEntrySet` (id, entry_id, set_number, reps, weight, distance, duration).
     - `app/exercise/schemas.py` — Pydantic create/response schemas.
     - `app/exercise/service.py` — CRUD + time-range query.
     - `app/api/exercise.py` — FastAPI router with `POST /exercise`, `GET /exercise`, `POST /exercise/sets`.
     - `alembic/versions/add_exercise_tables.py`
   - **Changes:**
     - Wire `app/api/exercise.py` into `app/main.py` under `/api/v1`.
     - Add `exercise_entries` relationship to `app/db/models.py` `User`.
   - **Acceptance:**
     - Migration applies cleanly.
     - `POST /api/v1/exercise` returns created entry with nested sets.

4. **P1-03: `app/sleep/` — sleep_entries + sleep_entry_stages**
   - **New Files:**
     - `app/sleep/models.py` — `SleepEntry` (id, user_id, start_time, end_time, duration_minutes, efficiency, score, source) and `SleepStage` (id, entry_id, stage_type, duration_minutes, start_time).
     - `app/sleep/schemas.py`
     - `app/sleep/service.py`
     - `app/api/sleep.py`
     - `alembic/versions/add_sleep_tables.py`
   - **Changes:**
     - Wire router in `app/main.py`.
     - Add `sleep_entries` relationship to `User`.
   - **Acceptance:**
     - Migration applies cleanly.
     - `GET /api/v1/sleep?start=...&end=...` returns entries with stage breakdown.

5. **P1-04: `app/measurements/` — custom_measurements**
   - **New Files:**
     - `app/measurements/models.py` — `CustomMeasurement` (id, user_id, metric_name, value, unit, measured_at, source, meta).
     - `app/measurements/schemas.py`
     - `app/measurements/service.py`
     - `app/api/measurements.py`
     - `alembic/versions/add_custom_measurements_table.py`
   - **Changes:**
     - Wire router in `app/main.py`.
     - Add `custom_measurements` relationship to `User`.
   - **Acceptance:**
     - `POST /api/v1/measurements` creates a row; `GET /api/v1/measurements?metric_name=waist` filters correctly.

6. **P1-05: `app/fasting/`, `app/mood/`, `app/water/` — simple models + services**
   - **New Files (per domain):**
     - `app/<domain>/models.py` — single table each:
       - `FastingEntry`: id, user_id, start_time, end_time, duration_minutes, source.
       - `MoodEntry`: id, user_id, score (1-10), notes, logged_at.
       - `WaterEntry`: id, user_id, amount_ml, logged_at, source.
     - `app/<domain>/schemas.py`
     - `app/<domain>/service.py`
     - `app/api/<domain>.py`
     - `alembic/versions/add_fasting_mood_water_tables.py` (single migration for all three to reduce churn)
   - **Changes:**
     - Wire all three routers in `app/main.py`.
     - Add relationships to `User`.
   - **Acceptance:**
     - One migration creates all three tables.
     - Each endpoint accepts POST/GET.
   - **Depends on:** P1-02, P1-03, P1-04 (follow same boilerplate pattern).

---

### Phase 2: Garmin Merge

7. **P2-01: Merge SparkyFitnessGarmin Python/FastAPI into `app/ingestion/garmin.py`**
   - **New File:** `app/ingestion/garmin.py`
   - **Changes:**
     - Implement `GarminIngestionService` with methods:
       - `parse_activity(payload: dict) -> list[HealthMetricCreate]` (maps to `MetricType.EXERCISE_MINUTES`, `STEPS`, `DISTANCE_KM`, `HEART_RATE`).
       - `parse_sleep(payload: dict) -> list[HealthMetricCreate]` (maps to sleep types).
       - `parse_body_composition(payload: dict) -> list[HealthMetricCreate]` (maps to `WEIGHT`, `BODY_FAT_PERCENT`).
     - Use `app.metrics.types.MetricType` and `app.metrics.schemas.HealthMetricCreate` to emit unified metric objects.
   - **Acceptance:**
     - Service unit test converts a sample Garmin webhook JSON into 3+ `HealthMetricCreate` objects with correct types/units.

8. **P2-02: Garmin webhook route in `app/api/garmin.py`**
   - **New File:** `app/api/garmin.py`
   - **Changes:**
     - `POST /garmin/webhook` — accept Garmin webhook payload, verify Garmin signature if a shared secret is configured (optional v1).
     - Route delegates to `GarminIngestionService` and then writes via `HealthMetricService`.
   - **Acceptance:**
     - Webhook endpoint returns `201` with `{"created": N, "skipped": M}`.
     - Duplicate `provider_id` entries are skipped (leverages existing dedup in `HealthMetricService.create_batch`).
   - **Depends on:** P2-01.

9. **P2-03: Webhook → health_metrics write pipeline**
   - **Changes:**
     - In `app/api/garmin.py`, after parsing, call `HealthMetricService(db).create_batch(user_id, batch)`.
     - Ensure `provider_id` is set to Garmin activity/sleep ID for dedup.
   - **Acceptance:**
     - After webhook delivery, `GET /api/v1/metrics?types=exercise_minutes&source=garmin` returns the new rows.
   - **Depends on:** P2-02, P0-03 (batch insert exists).

---

### Phase 3: AI Layer (Plate Pattern → Python)

10. **P3-01: `app/ai/base.py` — Agent, Tool, ToolRegistry base classes**
    - **New File:** `app/ai/base.py`
    - **Changes:**
      - `BaseAgent` (async `handle(data: dict) -> dict`).
      - `Tool` dataclass: name, description, parameters schema, handler coroutine.
      - `ToolRegistry`: `register(tool)`, `get(name)`, `list_tools() -> list[dict]` (OpenAI function-calling format).
    - **Acceptance:**
      - `ToolRegistry().list_tools()` emits JSON Schema compatible with OpenAI `functions`.

11. **P3-02: `app/ai/llm.py` — extend LLMService with `generate_structured()` + tool injection**
    - **File:** `app/services/llm_service.py` (extend) **or** new `app/ai/llm.py` (preferred to keep `services/` clean).
    - **Changes:**
      - Add `generate_structured(prompt: str, output_schema: type[BaseModel], tools: list[Tool] | None = None) -> BaseModel`.
      - Add `generate_with_tools(prompt: str, tools: list[Tool]) -> dict` (calls LLM with `functions` param, parses tool_calls).
      - Inject `ToolRegistry` tools into the system prompt when `tools` are provided.
    - **Acceptance:**
      - Calling `generate_structured` with `output_schema=SpikePredictionResponse` returns a parsed Pydantic model.
      - Calling `generate_with_tools` with a mock weather tool returns a tool_call request when the prompt asks for weather.
    - **Depends on:** P3-01.

12. **P3-03: `app/ai/agents/spike_predictor.py` — SpikePredictorAgent**
    - **New File:** `app/ai/agents/spike_predictor.py`
    - **Changes:**
      - Inherit from `BaseAgent`.
      - `handle(data)` expects `{"carbs_g": float, "protein_g": float, "fat_g": float, "current_glucose": float, "insulin_on_board": float}`.
      - Use `generate_structured()` to return `SpikePrediction` Pydantic model:
        - `predicted_peak_glucose: float`, `predicted_peak_time_minutes: int`, `confidence: float`, `factors: list[str]`.
      - System prompt includes nutrition science guardrails (no dosing advice).
    - **Acceptance:**
      - Agent returns a structured prediction in < 3s (OpenRouter gpt-4o-mini).
      - Confidence is clamped 0.0–1.0.
    - **Depends on:** P3-02.

13. **P3-04: `app/ai/agents/conversation.py` — structured ConversationAgent with tool access**
    - **New File:** `app/ai/agents/conversation.py`
    - **Changes:**
      - Replace the stub `ConversationAgent` in `app/agents/coordinator.py`.
      - Use `ToolRegistry` to inject:
        - `spike_predictor` tool (calls P3-03 agent)
        - `query_metrics` tool (calls `HealthMetricService`)
        - `pattern_summary` tool (calls `PatternService`)
      - Maintain conversation history in `data["history"]`.
    - **Acceptance:**
      - Asking "Will this meal spike me?" triggers the `spike_predictor` tool and returns a plain-language explanation + structured data.
    - **Depends on:** P3-01, P3-02, P3-03.

14. **P3-05: `app/ai/agents/pattern.py` — structured PatternAgent with cross-domain correlations**
    - **New File:** `app/ai/agents/pattern.py`
    - **Changes:**
      - Replace stub `PatternAgent` in `app/agents/coordinator.py`.
      - `handle(data)` with `action="correlate"` queries `health_metrics` for glucose + food + exercise + sleep in a window.
      - Use `generate_structured` to return `CorrelationInsight` model:
        - `domains: list[str]`, `insight_summary: str`, `confidence: float`, `suggested_actions: list[str]` (non-clinical).
    - **Acceptance:**
      - Correlating 7 days of data returns at least one insight mentioning two distinct domains (e.g., sleep and glucose).
    - **Depends on:** P3-02, P1 domain packages (for data to exist).

15. **P3-06: `app/ai/agents/meal_plan.py` — MealPlanAgent**
    - **New File:** `app/ai/agents/meal_plan.py`
    - **Changes:**
      - `handle(data)` accepts `dietary_restrictions`, `target_carbs_per_meal`, `preferences`.
      - Returns `MealPlan` structured model with meals and estimated macros.
      - Includes disclaimer: "This is educational meal inspiration, not a prescription."
    - **Acceptance:**
      - Returns a 3-meal plan with carb estimates; never includes insulin dosing.
    - **Depends on:** P3-02.

---

### Phase 4: External Providers

16. **P4-01: `app/ingestion/fitbit.py` — Fitbit OAuth + sync**
    - **New File:** `app/ingestion/fitbit.py`
    - **Changes:**
      - OAuth2 flow: `authorize_url`, `token_exchange`, `refresh_token`.
      - Sync endpoints: `fetch_activities`, `fetch_sleep`, `fetch_heart_rate`.
      - Map to `HealthMetricCreate` and write via `HealthMetricService`.
    - **New API File:** `app/api/fitbit.py` — `GET /fitbit/auth`, `GET /fitbit/callback`, `POST /fitbit/sync`.
    - **Acceptance:**
      - OAuth callback stores tokens on `User` (add `fitbit_access_token`, `fitbit_refresh_token`, `fitbit_expires_at` to `app/db/models.py`).
      - `POST /api/v1/fitbit/sync` returns `{"created": N}`.
    - **Depends on:** P0-03 (HealthMetricService batch write).

17. **P4-02: `app/ingestion/withings.py` — Withings webhook + sync**
    - **New File:** `app/ingestion/withings.py`
    - **New API File:** `app/api/withings.py`
    - **Changes:**
      - Implement Withings notification API subscription and webhook handler.
      - Map weight, heart rate, sleep data to `HealthMetricCreate`.
    - **Acceptance:**
      - `POST /api/v1/withings/webhook` processes weight notifications and writes to `health_metrics` with `source=withings`.
    - **Depends on:** P0-03.

18. **P4-03: `app/ingestion/strava.py` — Strava OAuth + sync**
    - **New File:** `app/ingestion/strava.py`
    - **New API File:** `app/api/strava.py`
    - **Changes:**
      - OAuth + activity fetch; map to `MetricType.EXERCISE_MINUTES`, `DISTANCE_KM`, `HEART_RATE`.
    - **Acceptance:**
      - `POST /api/v1/strava/sync` creates exercise metrics from recent activities.
    - **Depends on:** P0-03.

19. **P4-04: `app/ingestion/polar.py` — Polar sync**
    - **New File:** `app/ingestion/polar.py`
    - **New API File:** `app/api/polar.py`
    - **Changes:**
      - Polar AccessLink API v3; fetch training sessions and sleep.
    - **Acceptance:**
      - Sync endpoint writes rows with `source=polar`.
    - **Depends on:** P0-03.

---

### Phase 5: Multi-Provider Food

20. **P5-01: OpenFoodFacts integration**
    - **New File:** `app/food/providers/openfoodfacts.py`
    - **Changes:**
      - `search_by_name(query: str) -> list[FoodCreate]` using OpenFoodFacts REST API.
      - `search_by_barcode(barcode: str) -> FoodCreate | None`.
    - **Acceptance:**
      - Searching "banana" returns at least one `FoodCreate` with carbs > 0.
    - **Depends on:** P1-01 (food schemas/models exist).

21. **P5-02: USDA FoodData Central integration**
    - **New File:** `app/food/providers/usda.py`
    - **Changes:**
      - `search_usda(query: str, api_key: str) -> list[FoodCreate]`.
      - Cache results in Redis or short-term in-memory to respect rate limits.
    - **Acceptance:**
      - USDA search returns foods with macro breakdown.
    - **Depends on:** P5-01 (same pattern).

22. **P5-03: FoodPhotoAnalyzerAgent**
    - **New File:** `app/ai/agents/food_photo.py`
    - **Changes:**
      - Accepts base64 image or URL.
      - Calls LLM with vision capability (gpt-4o-mini supports vision via OpenRouter).
      - Returns structured `FoodPhotoAnalysis`: `detected_foods: list[str]`, `estimated_carbs_g: float`, `confidence: float`, `suggestions: list[str]`.
    - **Acceptance:**
      - Uploading a photo of a sandwich returns `detected_foods` containing "bread" and estimated carbs > 20g.
    - **Depends on:** P3-02 (structured generation + image support).

23. **P5-04: Food search service (aggregates all providers)**
    - **File:** `app/food/service.py` (extend)
    - **Changes:**
      - Add `search_all_providers(user_id: int, query: str) -> list[FoodResponse]` that queries:
        1. User’s personal `foods` table first (exact match).
        2. OpenFoodFacts.
        3. USDA.
      - Deduplicate by name + brand (fuzzy).
    - **Acceptance:**
      - `GET /api/v1/food/search?q=banana` returns personal + external results; personal results rank first.
    - **Depends on:** P5-01, P5-02, P1-01.

---

### Phase 6: Frontend

24. **P6-01: Health metrics dashboard (glucose + food + exercise + sleep)**
    - **New Files:**
      - `frontend/src/pages/HealthMetrics.tsx`
      - `frontend/src/hooks/useHealthMetrics.ts`
      - `frontend/src/components/charts/CombinedMetricChart.tsx`
    - **Changes:**
      - Add route `/health-metrics` in `frontend/src/App.tsx`.
      - Page shows:
        - Glucose chart (reuse `GlucoseChart`).
        - Food entries timeline.
        - Exercise minutes bar chart.
        - Sleep duration bar chart.
        - Unified date range selector (1D/7D/14D/30D).
      - Fetch from `GET /api/v1/metrics?types=...&start=...&end=...`.
    - **Acceptance:**
      - All four metric types visible on one page; range selector updates all charts.
    - **Depends on:** P0-04 (unified metrics endpoint), P1-01..P1-05 (domain data exists).

25. **P6-02: Food logging page**
    - **New File:** `frontend/src/pages/FoodLog.tsx`
    - **Changes:**
      - Route `/food` in `App.tsx`.
      - Features:
        - Search bar hitting `GET /api/v1/food/search?q=...` (P5-04).
        - Create food entry form (meal type, quantity, time).
        - Daily summary card (total carbs/protein/fat/calories).
      - Use `useMutation` + `useQuery` from `@tanstack/react-query`.
    - **Acceptance:**
      - User can search, select a food, log it, and see it appear in the daily list.
    - **Depends on:** P1-01, P5-04.

26. **P6-03: Exercise logging page**
    - **New File:** `frontend/src/pages/ExerciseLog.tsx`
    - **Changes:**
      - Route `/exercise` in `App.tsx`.
      - Form: activity type, duration, intensity, calories, start time.
      - List of recent entries; edit/delete actions.
    - **Acceptance:**
      - `POST /api/v1/exercise` from form; list updates on success.
    - **Depends on:** P1-02.

27. **P6-04: Sleep tracking page**
    - **New File:** `frontend/src/pages/SleepLog.tsx`
    - **Changes:**
      - Route `/sleep` in `App.tsx`.
      - Form: bedtime, wake time, quality score (1–10).
      - If sleep stages are available (from Garmin/Withings), show a stacked bar chart.
    - **Acceptance:**
      - Sleep entries visible; chart renders when stage data exists.
    - **Depends on:** P1-03.

28. **P6-05: AI chat interface with spike prediction tool**
    - **File:** `frontend/src/pages/Chat.tsx` (extend)
    - **Changes:**
      - Add "Spike Predictor" quick-action button in chat UI.
      - When triggered, open a modal/form: current glucose, planned carbs, protein, fat.
      - Submit calls backend agent (P3-03) and displays:
        - Predicted peak glucose and time.
        - Confidence meter.
        - Plain-language explanation.
      - Render tool calls differently from normal text (e.g., special card styling).
    - **Acceptance:**
      - User can click "Predict Spike", fill form, and see a structured prediction card in the chat thread.
    - **Depends on:** P3-03, P3-04.

---

## Files to Modify (Existing)

| File | What to modify |
|------|----------------|
| `app/db/models.py` | Add missing relationships (`foods`, `food_entries`, `exercise_entries`, `sleep_entries`, `custom_measurements`, `fasting_entries`, `mood_entries`, `water_entries`) to `User`. |
| `app/main.py` | Include new API routers (`exercise`, `sleep`, `measurements`, `fasting`, `mood`, `water`, `garmin`, `fitbit`, `withings`, `strava`, `polar`). |
| `app/agents/coordinator.py` | Replace stub agent classes with real imports from `app/ai/agents/...` once Phase 3 is complete. |
| `app/services/llm_service.py` | Deprecate inline safety keyword checks in favor of `app/ai/safety.py` (P0-05). Eventually replace with `app/ai/llm.py` calls if a full refactor is desired. |
| `frontend/src/App.tsx` | Add routes for `/health-metrics`, `/food`, `/exercise`, `/sleep`. |
| `frontend/src/types/index.ts` | Add TypeScript interfaces for new API responses (exercise, sleep, health metric query, spike prediction). |

---

## New Files (Summary)

### Backend
- `app/ai/__init__.py`
- `app/ai/safety.py` (P0-05)
- `app/ai/base.py` (P3-01)
- `app/ai/llm.py` (P3-02)
- `app/ai/agents/__init__.py`
- `app/ai/agents/spike_predictor.py` (P3-03)
- `app/ai/agents/conversation.py` (P3-04)
- `app/ai/agents/pattern.py` (P3-05)
- `app/ai/agents/meal_plan.py` (P3-06)
- `app/ai/agents/food_photo.py` (P5-03)
- `app/exercise/__init__.py`
- `app/exercise/models.py`
- `app/exercise/schemas.py`
- `app/exercise/service.py`
- `app/api/exercise.py`
- `app/sleep/__init__.py`
- `app/sleep/models.py`
- `app/sleep/schemas.py`
- `app/sleep/service.py`
- `app/api/sleep.py`
- `app/measurements/__init__.py`
- `app/measurements/models.py`
- `app/measurements/schemas.py`
- `app/measurements/service.py`
- `app/api/measurements.py`
- `app/fasting/__init__.py`
- `app/fasting/models.py`
- `app/fasting/schemas.py`
- `app/fasting/service.py`
- `app/api/fasting.py`
- `app/mood/__init__.py`
- `app/mood/models.py`
- `app/mood/schemas.py`
- `app/mood/service.py`
- `app/api/mood.py`
- `app/water/__init__.py`
- `app/water/models.py`
- `app/water/schemas.py`
- `app/water/service.py`
- `app/api/water.py`
- `app/ingestion/__init__.py`
- `app/ingestion/garmin.py` (P2-01)
- `app/api/garmin.py` (P2-02)
- `app/ingestion/fitbit.py` (P4-01)
- `app/api/fitbit.py`
- `app/ingestion/withings.py` (P4-02)
- `app/api/withings.py`
- `app/ingestion/strava.py` (P4-03)
- `app/api/strava.py`
- `app/ingestion/polar.py` (P4-04)
- `app/api/polar.py`
- `app/food/providers/openfoodfacts.py` (P5-01)
- `app/food/providers/usda.py` (P5-02)

### Alembic Migrations
- `alembic/versions/add_food_tables.py`
- `alembic/versions/add_exercise_tables.py`
- `alembic/versions/add_sleep_tables.py`
- `alembic/versions/add_custom_measurements_table.py`
- `alembic/versions/add_fasting_mood_water_tables.py`

### Frontend
- `frontend/src/pages/HealthMetrics.tsx`
- `frontend/src/hooks/useHealthMetrics.ts`
- `frontend/src/components/charts/CombinedMetricChart.tsx`
- `frontend/src/pages/FoodLog.tsx`
- `frontend/src/hooks/useFood.ts`
- `frontend/src/pages/ExerciseLog.tsx`
- `frontend/src/hooks/useExercise.ts`
- `frontend/src/pages/SleepLog.tsx`
- `frontend/src/hooks/useSleep.ts`

---

## Dependencies & Execution Order

```
P0-05  ────────────────────────────────────────┐
                                                  ▼
P1-01 ──► P1-02 ──► P1-03 ──► P1-04 ──► P1-05  ──┐
                                                    ▼
P2-01 ──► P2-02 ──► P2-03                         │ (needs P0-03 batch write)
                                                    ▼
P3-01 ──► P3-02 ──► P3-03, P3-04, P3-05, P3-06  ──┤
                                                    ▼
P4-01 .. P4-04  ──────────────────────────────────┤ (needs P0-03)
                                                    ▼
P5-01 ──► P5-02 ──► P5-03 ──► P5-04               │ (needs P1-01, P3-02)
                                                    ▼
P6-01 .. P6-05  ───────────────────────────────────┘ (needs P0-04, P1-01..P1-05, P3-03..P3-04)
```

**Recommended sprint order:**
1. Complete P0-05 (safety scaffold).
2. Run P1 in sequence (01 → 02 → 03 → 04 → 05) because each new domain package teaches the boilerplate for the next.
3. Run P2 (Garmin) immediately after P1 because it exercises the unified `health_metrics` write path.
4. Run P3 in order (01 → 02 → 03..06) because base classes and LLM structured generation are prerequisites for all agents.
5. Run P4 providers in parallel (they are independent once P0-03 exists).
6. Run P5 food providers after P1-01 and P3-02.
7. Run P6 frontend pages after their respective backend phases are complete.

---

## Risks & Clarifications

1. **Alembic migration ordering:** The existing migration `add_health_metrics_and_aggregates.py` has `down_revision = None`. If the database already has other migrations applied in production, the new migrations must declare correct `down_revision` chains. **Action:** Inspect `alembic history` before generating new migrations and set `down_revision` explicitly.

2. **User model bloat:** Adding 8+ relationships to `User` (`foods`, `exercise_entries`, `sleep_entries`, etc.) may slow eager-loading paths. **Mitigation:** Use `lazy="selectin"` only where needed; keep defaults as `lazy="select"` for new relationships.

3. **Duplicate schema definitions:** `ContextEvent` in `app/db/models.py` already has `event_type` fields for meals, exercise, sleep. The new domain tables (P1) create a second storage path. **Decision needed:** Should the unified `POST /api/v1/metrics` endpoint (P0-04) remain the canonical ingestion path, while domain tables (P1) serve as rich-detail stores? If so, document this dual-write strategy in `DEVELOPMENT.md`.

4. **Frontend route collision:** The existing `EventsPage` (`/events`) is a generic event logger. New pages (`/food`, `/exercise`, `/sleep`) may duplicate functionality. **Mitigation:** Deprecate generic `/events` gradually; keep it as a fallback quick-log while domain pages become primary.

5. **OpenRouter vision for P5-03:** Not all models on OpenRouter support image inputs. Confirm `gpt-4o-mini` via OpenRouter accepts base64 image URLs in the messages payload. **Fallback:** If vision fails, use a description-based flow.

6. **Test coverage:** The `tests/` directory is empty. Every backend task above should include a corresponding test file. **Recommendation:** Add a parallel testing task after each domain phase, or batch them at the end of each phase.

7. **No-auth placeholder:** API routes currently use `user_id: int = Query(..., ge=1)` as a placeholder. As the app approaches production, auth dependency injection must replace this. **Note:** Keep the placeholder pattern consistent across all new routes so the global swap is a single refactor later.
