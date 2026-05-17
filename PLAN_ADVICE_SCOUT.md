# Next-Phase Hardening — Scout Report

## File Map

### Core chat pipeline (7 files, ~1350 lines)

| File | Lines | Role |
|------|-------|------|
| `app/api/chat.py` | ~495 | HTTP contract, conversation persistence, context building |
| `app/agents/coordinator.py` | ~325 | 5-agent pipeline w/ safety→ingestion→pattern→conversation→summary |
| `app/services/llm_service.py` | ~890 | RAG context, provider calls, rule-based fallback, pattern summarization |
| `app/services/pattern_service.py` | ~1000 | Diabetes analytics engine (TIR, spikes, overnight lows, exercise, etc.) |
| `app/ai/safety.py` | ~320 | Safety scaffold, policy violations, emergency detection |
| `app/api/patterns.py` | ~320 | REST endpoints wrapping PatternService |
| `app/api/users.py` | ~280 | Nightscout config endpoints |

### Food providers (5 files, ~365 lines)

| File | Lines | Role |
|------|-------|------|
| `app/food/providers/openfoodfacts.py` | ~130 | Free food API — name/barcode search |
| `app/food/providers/usda.py` | ~105 | USDA FoodData Central — name search |
| `app/food/service.py` | ~255 | Multi-tier search: local→OpenFoodFacts→USDA |
| `app/food/models.py` | ~40 | ORM models (Food, FoodEntry) |
| `app/api/food.py` | ~30 | REST routes |

### CGM ingestion (4 files, ~600 lines)

| File | Lines | Role |
|------|-------|------|
| `app/services/dexcom_service.py` | ~400 | OAuth, token refresh, glucose sync |
| `app/services/nightscout_service.py` | ~360 | Nightscout API, glucose sync |
| `app/services/sync_service.py` | ~530 | Periodic sync orchestration |
| `app/services/meal_service.py` | ~280 | Nutrition tracking service |
| `app/api/glucose_ext.py` | ~260 | Dexcom/Nightscout sync endpoints |

### Test infrastructure (6 files, ~1970 lines)

| File | Lines | Role |
|------|-------|------|
| `tests/__init__.py` | 21 | PostgreSQL type compat patches for SQLite |
| `tests/conftest.py` | 185 | Shared fixtures (DB engine, users, glucose dataset, events) |
| `tests/test_pattern_service.py` | 1047 | 37 PatternService tests (7 classes) |
| `tests/test_llm_service.py` | 244 | 25 LLM service tests |
| `tests/ai/test_safety.py` | 320 | 30 safety scaffold tests |
| `tests/test_chat_pipeline.py` | 150 | 9 chat pipeline tests |

### Auth/Security endpoints (3 files)

| File | Lines | Role |
|------|-------|------|
| `app/api/auth.py` | ~370 | Register, login, Dexcom OAuth callback, email verification |
| `app/core/security.py` | ~120 | JWT, password hashing, dependency guards |
| `app/db/models.py` | ~380 | Core ORM: User, GlucoseReading, ContextEvent, Conversation |

### Domain APIs (15 route files)

All at `app/api/*.py` — exercise, sleep, food, metrics, fasting, mood, water, measurements, strava, garmin, fitbit, withings, polar, glucose, events.

---

## Likely Test Targets (priority-ordered)

### 1. Auth endpoint integration (HIGH)
- **Routes:** `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/dexcom/callback`
- **Test patterns needed:**
  - Register → verify user created + password hashed
  - Login → verify JWT issued
  - Duplicate email → 400
  - Unauthenticated access → 401
  - Dexcom callback with mocked `DexcomService`
- **Why now:** Every other integration test depends on auth working. No tests exist.
- **Fixture:** Use existing `db_session` + `test_user` from conftest.py
- **Mock surface:** No mocking needed for register/login (DB only). Dexcom callback needs `DexcomService.exchange_code_for_tokens` mocked.

### 2. Chat endpoint DB-backed integration (HIGH)
- **Routes:** `POST /api/v1/chat`, `POST /api/v1/chat/stream`
- **Test patterns needed:**
  - Full pipeline: user message → coordinator → safety → LLM fallback → persisted conversation message
  - Emergency keyword → short-circuits to escalation response
  - Streaming endpoint yields valid SSE chunks
  - Existing conversation context is retrieved
- **Why now:** Only unit-level tests exist (9 tests, all DB-free). The real chat pipeline has never been exercised with a DB + coordinator.
- **Fixture:** Existing `db_session` + `test_user` + `db_engine` in conftest.py
- **Mock surface:** `LLMService.generate_response` should be monkeypatched to return deterministic text. The rule-based fallback works without mocking.

### 3. Dexcom/Nightscout service tests (MEDIUM)
- **Services:** `DexcomService`, `NightscoutService`
- **Test patterns needed:**
  - Token exchange with mocked HTTP (httpx)
  - Token refresh with short-expiry + auto-refresh
  - Glucose sync with mocked API responses
  - Error handling: API down, invalid token, rate limit
  - Deduplication (same timestamp/source already exists)
- **Why now:** These hit real HTTP endpoints. No tests exist. Breaking changes are invisible.
- **Mock surface:** `httpx.AsyncClient` needs mocking. Use `pytest-httpx` or `respx` (neither installed).

### 4. Food provider tests (MEDIUM)
- **Providers:** `OpenFoodFactsClient`, `USDAClient`, `FoodService`
- **Test patterns needed:**
  - OpenFoodFacts name search returns parsed products
  - OpenFoodFacts barcode search returns single product
  - USDA name search returns parsed items
  - USDA with no API key → empty results (no crash)
  - Multi-tier search: local cache hit → no external call
  - Network failure → graceful empty list
  - Malformed API response → skips without crashing
- **Why now:** External API integration, no tests. Caching logic could corrupt DB.
- **Mock surface:** `httpx.AsyncClient` needs mocking. `pytest-httpx` or `respx`.

### 5. Pattern API endpoint tests (MEDIUM)
- **Routes:** `POST /api/v1/patterns/analyze`, `POST /api/v1/patterns/tir`, `POST /api/v1/patterns/spikes`
- **Test patterns:**
  - With DB data → correct analysis returned
  - Empty DB → graceful result
- **Note:** PatternService has 37 tests already. These would be thin HTTP wrappers.
- **Mock surface:** Minimal — PatternService can use real DB.

### 6. Safety scaffold post-LLM validation (LOW)
- **What's missing:**
  - After `coordinator.process_chat_message()` returns, the chat endpoint does NOT run the response through SafetyAgent again
  - If the LLM generates dosing advice, it would be saved and returned to the user
- **Test pattern:** Mock LLM to return "take 5 units" → verify SafetyAgent catches it
- **Fix + test together**

### 7. Warning cleanup targets (LOW)
| File | Issue | Count |
|------|-------|-------|
| `app/*/schemas.py` (8 files) | Pydantic V2 `class Config:` → `model_config` | ~15 |
| `app/db/base.py:3:6` | `declarative_base()` → SQLAlchemy 2.0 `orm.declarative_base()` | 1 |
| `app/db/models.py` | `datetime.utcnow` in Column defaults | 10 |
| `app/core/logging_config.py:84` | `datetime.utcnow().isoformat()` | 1 |
| `app/api/glucose_ext.py:55,101` | `datetime.utcnow()` in sync endpoints | 2 |
| `app/ingestion/garmin.py:46,111,161` | `datetime.utcnow()` in Garmin parser | 3 |
| `app/config.py:103` | `class Config:` → `model_config` | 1 |

**Total warning sources:** ~33 locations. Fixing all ~432 warnings requires touching ~12 files.

---

## Implementation Notes

### Test infrastructure gaps

1. **No HTTP mocking library installed.** `httpx` is a dependency but `pytest-httpx` or `respx` are not. Any test that hits an external API needs one. Recommend `pytest-httpx`.
2. **No FastAPI TestClient usage.** No test uses `TestClient(app)`. The test_withings example exists at `app/api/withings.py` but isn't tested.
3. **SQLite fixture creates only 6 core tables.** This works for pattern/LLM tests but `HealthMetric`, `ExerciseEntry`, `SleepEntry`, `Food`, `FastingEntry`, `MoodEntry`, `WaterEntry` tables don't exist. Routes that access those will fail in tests.
4. **No `.env.test` or `pytest`-specific config.** `get_settings()` reads from real environment variables. Different behavior between dev and CI.

### Coordinator wiring note

`main.py` lifespan sets `app.state.coordinator = coordinator` but `chat.py` does:
```python
from app.main import app as fastapi_app
coordinator = getattr(fastapi_app.state, 'coordinator', None)
```
This works at runtime but NOT in tests that create a `TestClient` — because `test_app` is a different `FastAPI()` instance. The regression test in `test_chat_pipeline.py` monkeypatches `app.main` to work around this. A real TestClient test needs to do the same.

### Provider failures — default behavior

All external providers handle failures gracefully:
- `DexcomService` returns empty readings on any error
- `NightscoutService` returns empty on error
- `OpenFoodFactsClient` returns `[]` on HTTP error, `None` on barcode error
- `USDAClient` returns `[]` when no API key or HTTP error
- `LLMService` falls back to `_rule_based_response` when provider fails

This is good for resilience but makes silent failures invisible without tests.

### LLM service singleton

`app/services/llm_service.py` has a module-level singleton (`_llm_service`) with `get_llm_service()` / `set_llm_service()` at lines 877-895. Tests that create their own `LLMService` instance won't affect the singleton, which could cause confusion.

### Food service note

`app/food/service.py` has a method name collision: `search_foods` is defined twice (lines 49 and 62). The second definition at line 62 overrides the first. It also calls `self.search_foods()` to search local DB — this is self-recursive. The second `search_foods` at line 62 is the one that does multi-provider search.

### Nutrition API timeouts

All httpx-based providers use `timeout=15.0`. The LLM service uses `timeout=60.0`. These are not configurable.

---

## File-Specific Annotations

### `app/api/chat.py` — `_build_context()`
- Calls PatternService directly (not through coordinator)
- Three sequential DB queries inside the coordinator request — okay for MVP but could be optimized
- `_build_context` runs inside both streaming and non-streaming endpoints (duplicated logic)

### `app/services/llm_service.py` — `retrieve_context()`
- Fetches glucose + events + conversation history + calls PatternService
- Duplicates `_build_context()` from chat.py
- `_build_system_prompt()` omits conversation history — it's passed separately in `generate_response()`

### `app/agents/coordinator.py` — `SafetyAgent`
- Has its OWN emergency keyword list embedded (lines ~415-420) which is DUPLICATED from `app/ai/safety.py`
- If one is updated, the other will drift
- The coordinator's `SafetyAgent` only checks its own keyword list, doesn't delegate to `SafetyScaffold.validate()`

### `app/services/dexcom_service.py` — `get_glucose_readings()`
- Returns `List[GlucoseReading]` DB objects, not raw API responses
- Deduplicates by `(user_id, timestamp, source)` — silently skips duplicates
- No start_date/end_date parameters — it's "sync recent data" or nothing

### `app/api/glucose_ext.py` — `sync_dexcom()`
- Uses `datetime.utcnow()` instead of `datetime.now(timezone.utc)`
- Uses settings-level Dexcom credentials, not user-stored tokens
- Nightscout sync endpoint reads `NIGHTSCOUT_URL` from settings, not user — likely a bug from the Phase 3 W7 work

---

## Subagent-Friendly Work Packages

### Work Package A: Auth API tests (1 subagent)
- **Files:** `tests/test_api_auth.py` (new)
- **Models:** `openrouter/deepseek/deepseek-v4-flash`
- **Effort:** ~150 lines, 8-10 tests
- **Depends on:** nothing beyond existing conftest.py
- **Key assertions:** register → login → JWT → protected endpoint → 401 on bad token → duplicate email → 400

### Work Package B: Chat integration test (1 subagent)
- **Files:** `tests/test_chat_integration.py` (new)
- **Models:** same
- **Effort:** ~120 lines, 5-6 tests
- **Depends on:** need `TestClient` pattern, coordinator monkeypatch, LLM stub
- **Key assertions:** full pipeline runs, emergency short-circuits, response saved to DB

### Work Package C: Dexcom/Nightscout service tests (1 subagent)
- **Files:** `tests/test_dexcom_service.py`, `tests/test_nightscout_service.py` (new)
- **Models:** same
- **Effort:** ~200 lines for both, ~15 tests
- **Depends on:** `pytest-httpx` or `respx` installed first
- **Key assertions:** token exchange, sync, dedup, error handling

### Work Package D: Food provider tests (1 subagent)
- **Files:** `tests/test_food_providers.py` (new)
- **Models:** same
- **Effort:** ~150 lines, 10-12 tests
- **Depends on:** `pytest-httpx` or `respx` installed first
- **Key assertions:** name search, barcode search, empty API key, network failure

### Work Package E: Safety post-LLM validation + fix (1 subagent)
- **Files:** `app/api/chat.py`, `app/agents/coordinator.py`, `tests/test_chat_pipeline.py`
- **Models:** same
- **Effort:** ~80 lines, 2-3 tests + fix
- **Depends on:** existing chat pipeline tests
- **Key assertion:** LLM response with dosing advice → post-LLM SafetyAgent catches it

### Work Package F: Warning cleanup (1 subagent)
- **Files:** ~12 files in `app/*/schemas.py`, `app/db/base.py`, `app/db/models.py`, `app/config.py`, `app/core/logging_config.py`, `app/api/glucose_ext.py`, `app/ingestion/garmin.py`
- **Models:** same
- **Effort:** ~60 edits across 12 files
- **Depends on:** nothing
- **Risks:** High change surface for cosmetic changes. Run test suite after.

### Work Package G: Nightscout user-level URL fix (1 subagent)
- **Files:** `app/api/glucose_ext.py`
- **Effort:** ~30 lines
- **Depends on:** Nothing
- **Fix:** Nightscout sync should use `user.nightscout_url` instead of `settings.NIGHTSCOUT_URL`

### Work Package H: Coordinator SafetyAgent → SafetyScaffold pipeline (1 subagent)
- **Files:** `app/agents/coordinator.py`, `tests/test_chat_pipeline.py`
- **Effort:** ~50 lines
- **Depends on:** Nothing
- **Fix:** Make `SafetyAgent.handle()` delegate to `SafetyScaffold.validate()` instead of duplicating keyword logic
