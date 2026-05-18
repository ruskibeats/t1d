# Next Phase Plan — Production Hardening & Test Depth

## Current State

Chat pipeline is real. Coordinator is wired via `app.state`. 101 tests pass. Wave 1/2 reviews done. But:

- Chat endpoint has no true DB-backed integration test hitting the real coordinator pipeline
- Dexcom/Nightscout services have no tests (mocked or otherwise)
- Food providers have no tests
- Test infrastructure uses SQLite — brittle, limited
- 432 warnings drown out real signals
- No post-LLM safety validation on assistant responses

---

## Strategy

Run 4 worker waves in parallel, each as a subagent with `openrouter/deepseek/deepseek-v4-flash`. Each wave produces code + test + outlines. Fixer wave runs after to catch cross-wave conflicts.

Workers are standalone — no inter-worker dependencies. Each can go independently.

---

## Wave 1: Chat Integration Test (The Critical One)

**Goal:** True DB-backed test that posts to `/api/v1/chat` and verifies the full pipeline: safety → data_ingestion → pattern → conversation → DB persistence of messages.

### Worker: `w1-chat-integration`
**File:** `tests/test_chat_integration.py`

Tasks:

1. **Add `app.state.coordinator` to test FastAPI app** — reuse the existing `conftest.py` fixture but create a test `FastAPI` instance with the coordinator wired.

2. **Write `test_chat_full_pipeline(db_session, test_user)`**
   - Insert 5 glucose readings and 1 meal `ContextEvent`
   - Build a `TestClient` with a FastAPI app that has the coordinator on state
   - POST `/api/v1/chat` with `{"message": "How were my glucose levels today?"}`
   - Assert `200`, assert `response_text` is non-empty
   - Assert a `ConversationMessage` row was written to DB for user and assistant
   - Assert `conversation_id` is returned

3. **Write `test_chat_safety_short_circuit(db_session, test_user)`**
   - POST with `{"message": "I can't wake my son up, his blood sugar is severe low"}`
   - Assert response contains safety escalation language, not a normal answer
   - Assert no regular `ConversationMessage` was saved (or it was flagged)

4. **Write `test_chat_new_user_no_data(db_session, test_user)`**
   - No glucose readings, no events
   - POST `/api/v1/chat` with `{"message": "Hello"}`
   - Assert response is friendly and non-empty (fallback path)
   - Assert message saved to DB

5. **Write `test_chat_streaming_endpoint(db_session, test_user)`**
   - Same setup as full pipeline test
   - POST `/api/v1/chat/stream` with SSE
   - Assert chunks arrive, final chunk has `is_complete=True`

**Dependencies:** `conftest.py` fixtures (existing), `httpx.AsyncClient` (already in deps)

**Output:** `tests/test_chat_integration.py` — 5 tests

**Acceptance:** `python3 -m pytest tests/test_chat_integration.py -v` → 5 passed

---

## Wave 2: Mocked External Service Tests

**Goal:** Coverage for Dexcom, Nightscout, and food providers with mocked HTTP responses. No real API calls.

### Worker 2a: `w2-dexcom-tests`
**File:** `tests/test_dexcom_service.py`

Tasks:

1. **Mock `httpx.AsyncClient`** — use `respx` or `httpx.MockTransport` to intercept HTTP calls
2. **Test `exchange_code_for_tokens`** — mock POST to Dexcom OAuth token endpoint → return mock tokens
3. **Test `refresh_access_token`** — mock token refresh → verify expiry update
4. **Test `get_glucose_readings`** — mock GET with sample Dexcom JSON → verify parsed readings match structure
5. **Test `get_glucose_readings` with empty response** — no readings → graceful empty list
6. **Test `sync_glucose_data`** — mock sequence: fetch → dedupe → insert → confirm DB rows
7. **Test `sync_glucose_data` with network error** → `DexcomServiceError` raised
8. **Test invalid token response** → `DexcomServiceError` with auth message

**Acceptance:** 6–8 tests, all use mocked HTTP, no network calls

### Worker 2b: `w2-nightscout-tests`
**File:** `tests/test_nightscout_service.py`

Tasks:

1. **Mock `httpx.AsyncClient`** — use same approach as Dexcom
2. **Test `_test_connection`** — mock success → return `True`
3. **Test `_test_connection` failure** — mock 401 → return `False`
4. **Test `get_glucose_readings`** — mock Nightscout SGV entries → verify parsed to `GlucoseReading` structure
5. **Test `sync_glucose_data`** — mock fetch → dedupe by timestamp → insert → confirm count
6. **Test `sync_glucose_data` with no new data** — empty API response → 0 inserted
7. **Test `sync_glucose_data` with API error** → `NightscoutServiceError`

**Acceptance:** 5–7 tests, all mocked

### Worker 2c: `w2-food-provider-tests`
**File:** `tests/test_food_providers.py`

Tasks:

1. **Mock `httpx.AsyncClient`** for both `OpenFoodFactsClient` and `USDAClient`
2. **OpenFoodFacts: `search_by_name`** — mock GET → return sample JSON with products → verify parsed nutrients (carbs, protein, fat, calories)
3. **OpenFoodFacts: `search_by_barcode`** — mock GET → return single product → verify parsing
4. **OpenFoodFacts: empty response** → returns empty list
5. **USDA: `search_by_name`** — mock GET → return sample JSON → verify nutrient extraction
6. **USDA: empty or missing API key** → returns empty list gracefully
7. **FoodService: `search_foods`** — test multi-tier: local → OpenFoodFacts → USDA fallback
8. **FoodService: cache external result** — search → external returns → stored in local `Food` table → search again returns local

**Acceptance:** 6–8 tests, all mocked

---

## Wave 3: Postgres Test Strategy + Warning Cleanup

**Goal:** Replace SQLite test hack with proper Postgres for integration tests. Eliminate the 432 warnings.

### Worker 3a: `w3-postgres-test-infra`
**File:** `tests/conftest.py` (modify), `tests/postgres_conftest.py` (new)

Tasks:

1. **Create `tests/postgres_conftest.py`** — environment-aware conftest that checks for `TEST_DATABASE_URL` env var
2. **When `TEST_DATABASE_URL` is set** — use real Postgres engine, run full `Base.metadata.create_all()`, use transactional rollback per test
3. **When not set** — fall back to current SQLite strategy for local/dev runs
4. **Add `pytest.mark.integration` marker** — tag tests that need Postgres
5. **Document in `CONTRIBUTING.md`** — how to run with Postgres, `TEST_DATABASE_URL=postgresql+asyncpg://... pytest -m integration`
6. **Verify the full table set** — `Base.metadata.create_all()` must succeed against Postgres. If duplicate index issues exist in the model definitions, fix them now (e.g., `FastingEntry` has both `index=True` and explicit `Index` with same name)

**Acceptance:** `TEST_DATABASE_URL=... pytest tests/ -m integration` → 100+ tests pass with Postgres

### Worker 3b: `w3-warning-cleanup`
**Tasks (code edits across 5–6 files):**

1. **Pydantic V2 `config` deprecation** — files like `app/measurements/schemas.py`, `app/fasting/schemas.py`, `app/mood/schemas.py`, `app/config.py`, `app/core/security.py`, `app/core/errors.py`
   - Replace `class Config:` with `model_config = ConfigDict(...)` in each Pydantic model
2. **SQLAlchemy `declarative_base()` deprecation in `app/db/base.py`** — change import from `sqlalchemy.ext.declarative` to `sqlalchemy.orm`
3. **`datetime.utcnow()` in `app/core/logging_config.py`** — switch to `datetime.now(timezone.utc)`
4. **`datetime.utcnow()` in SQLAlchemy `server_default` / `default` across models** — use `func.now()` or `datetime.now(timezone.utc)` as appropriate
5. **`__import__` hanger-on** — any remaining inline import pattern

**Acceptance:** Run `python3 -m pytest tests/ -q 2>&1 | grep "warnings"` → 0 warnings (or < 10 for SQLAlchemy minor issues)

---

## Wave 4: Post-LLM Safety Validation

**Goal:** Validate assistant responses through SafetyScaffold before saving/returning to user.

### Worker: `w4-post-llm-safety`
**File:** `app/agents/coordinator.py` (modify), `tests/test_post_llm_safety.py` (new)

Tasks:

1. **Add post-LLM safety check in `process_chat_message()`** — after `ConversationAgent` returns the response text, run:
   ```python
   safety_result = await self.agents["safety"].handle({
       "content": response["response"],
       "content_type": "assistant_response",
       "user_id": user_id,
       ...
   })
   ```
2. **If safety fails** — strip or override the response with a safe message + log the violation
3. **If safety passes** — return the response as-is
4. **Test: safe response** — normal pattern summary → passes post-check
5. **Test: response with dosing advice** — "You should take 5 units of insulin" → caught by post-check, replaced with safety message
6. **Test: response with missing disclaimer** — medical-sounding text without disclaimer → flagged
7. **Test: edge case** — empty response → passes through unchanged
8. **Test: borderline** — "Consider discussing with your doctor about adjusting insulin" → passes disclaimer rules

**Acceptance:** 5 tests in `tests/test_post_llm_safety.py`, all passing. Coordinator now applies post-LLM safety validation.

---

## Worker Summary Table

| Wave | Worker | Files | Tests | Model | Est. Runtime |
|------|--------|-------|-------|-------|-------------|
| 1 | w1-chat-integration | `tests/test_chat_integration.py` | 5 | `openrouter/deepseek/deepseek-v4-flash` | ~3 min |
| 2a | w2-dexcom-tests | `tests/test_dexcom_service.py` | 6–8 | same | ~3 min |
| 2b | w2-nightscout-tests | `tests/test_nightscout_service.py` | 5–7 | same | ~3 min |
| 2c | w2-food-provider-tests | `tests/test_food_providers.py` | 6–8 | same | ~3 min |
| 3a | w3-postgres-test-infra | `tests/conftest.py`, `tests/postgres_conftest.py` | infra change | same | ~5 min |
| 3b | w3-warning-cleanup | 6+ model/schema files | infra change | same | ~3 min |
| 4 | w4-post-llm-safety | `app/agents/coordinator.py`, `tests/test_post_llm_safety.py` | 5 | same | ~3 min |
| — | fixer-wave3 | cross-wave conflict resolution | — | same | ~3 min |

All waves can run in parallel. Fixer wave runs after all complete.

---

## Execution Plan

```text
t=0     Launch all 7 workers in parallel
        │
t=+3m   Workers deliver artifacts
        │
t=+5m   Parallel py_compile + pytest verify on each artifact
        │
t=+6m   Launch fixer-wave3 to resolve cross-file conflicts
        │
t=+9m   Full test suite: pytest tests/ -q
        │
t=+10m  Done
```

### Launch command pattern for each worker:

```
subagent({
  agent: "<worker-name>",
  model: "openrouter/deepseek/deepseek-v4-flash",
  task: "Read SKILL.md for context then execute the task spec..."
})
```

---

## Acceptance Criteria (Final)

- [ ] `tests/test_chat_integration.py` — 5 tests, DB-backed, full pipeline
- [ ] `tests/test_dexcom_service.py` — 6+ tests, all mocked
- [ ] `tests/test_nightscout_service.py` — 5+ tests, all mocked
- [ ] `tests/test_food_providers.py` — 6+ tests, all mocked
- [ ] Postgres test infrastructure — `TEST_DATABASE_URL` env var support, `pytest.mark.integration`
- [ ] Warnings — < 10 (ideally 0)
- [ ] Post-LLM safety validation — coordinator checks assistant responses before returning
- [ ] `tests/test_post_llm_safety.py` — 5 tests
- [ ] Full suite: `160+ passed, < 10 warnings`

---

## Risk Notes

| Risk | Mitigation |
|------|-----------|
| Postgres test infra may not have a Postgres instance available | Fall back to SQLite when `TEST_DATABASE_URL` unset; document Postgres setup |
| Model index conflicts block full `create_all` | Fix `FastingEntry` and any other duplicate-index models in the same wave |
| Warning cleanup may touch 10+ files | Worker lists exact files; each is a simple mechanical replacement |
| Post-LLM safety may break chat if over-sensitive | Conservative threshold — only catch clear dosing/treatment violations, not borderline educational language |
| Deepseek model may still have rate/downtime issues | Fallback to `openrouter/owl-alpha` or `openrouter/google/gemini-2.0-flash-lite` |
