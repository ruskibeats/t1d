# T1D Companion — Implementation Plan

## Current State Assessment

| Area | Status | Gap |
|------|--------|-----|
| Database schema (models.py) | ✅ Complete | — |
| API routes (18 routers) | ✅ Complete | — |
| Pydantic schemas | ✅ Complete | — |
| Safety system (SafetyScaffold) | ✅ Complete | — |
| Pattern detection engine | ✅ Complete | — |
| LLM service (multi-provider) | ⚠️ Partial | No real provider configured by default |
| Agent coordinator | ❌ Stubs | All 5 agents return placeholder data |
| Chat endpoint | ❌ Fake | Keyword-matching instead of LLM calls |
| RAG pipeline | ❌ Broken | Returns raw readings, no pattern summaries |
| Tests | ❌ Near-zero | 1 file (safety only), no integration tests |
| Frontend | ⚠️ Skeleton | Demo data only, no real API auth |
| Sync/background tasks | ❌ Missing | No Celery, no periodic sync |
| Food providers | ❌ Stubs | OpenFoodFacts/USDA not implemented |
| Wearable ingestion | ❌ Stubs | Garmin/Fitbit/Polar/Strava/Withings are empty |

---

## Phase 1: Make the Chat Pipeline Real

**Goal:** A user can register, log in, send a chat message, and get a real LLM response grounded in their data.

### 1.1 Wire up the Agent Coordinator

`app/agents/coordinator.py` — replace stubs with real delegation:

- **`DataIngestionAgent.handle()`** → call `LLMService.retrieve_context()` to get real glucose readings, events, and pattern summaries from the DB
- **`PatternAgent.handle()`** → call `PatternService.calculate_time_in_range()`, `detect_post_meal_spikes()`, `detect_overnight_hypoglycemia()` and return structured results
- **`ConversationAgent.handle()`** → call `LLMService.generate_response()` with the real message + context + patterns
- **`SummaryAgent.handle()`** → call `LLMService.summarize_patterns()` for natural language summaries
- **`SafetyAgent`** → already works, delegates to `SafetyScaffold`

Each agent's `handle()` should accept the same `dict` interface but delegate to the real service layer instead of returning placeholders.

### 1.2 Fix the Chat Endpoint

`app/api/chat.py` — replace the fake `_generate_ai_response()` keyword matcher:

- Remove the hardcoded if/else keyword tree (`if "spike" in message_lower`...)
- Replace with a call to `AgentCoordinator.process_chat_message()`
- The endpoint already saves user/AI messages to the DB — keep that
- The `_build_context()` helper already fetches real glucose and events — keep that, but also include pattern analysis results
- Wire the streaming endpoint (`/chat/stream`) to use the same pipeline with SSE chunks from the LLM service

### 1.3 Fix the RAG Pipeline

`app/services/llm_service.py` — `retrieve_context()` should return pattern summaries, not just raw data:

- After fetching glucose readings and events, call `PatternService.calculate_time_in_range()` and include the TIR summary
- Call `PatternService.detect_post_meal_spikes()` and include spike count
- Call `PatternService.detect_overnight_hypoglycemia()` and include overnight low count
- The system prompt builder (`_build_system_prompt()`) already knows how to render pattern data — it just never receives it

### 1.4 Default to a Working LLM Provider

`app/config.py` + `app/services/llm_service.py`:

- The default provider is `openrouter` but no API key is configured
- Add a fallback chain: try configured provider → if no key, use a simple rule-based response generator that still uses the RAG context (so the pipeline works end-to-end without an API key)
- This lets the system be testable without external dependencies

### 1.5 Write Integration Tests for the Chat Pipeline

`tests/test_chat_pipeline.py`:

- Test the full flow: register → login → send chat message → get response
- Use a test database (SQLite in-memory or test Postgres)
- Mock the LLM provider to return deterministic responses
- Verify: safety check runs, context is retrieved, response is saved to DB
- Test emergency keyword detection triggers escalation
- Test that dosing advice is blocked by post-LLM safety validation

**Phase 1 Acceptance Criteria:**
- [ ] `AgentCoordinator.process_chat_message()` runs the full pipeline with real services
- [ ] Chat endpoint returns LLM-generated (or rule-based fallback) responses grounded in user data
- [ ] RAG context includes pattern summaries, not just raw readings
- [ ] Streaming endpoint works with the real pipeline
- [ ] 10+ integration tests pass for the chat flow

---

## Phase 2: Test Coverage

**Goal:** Core business logic has unit tests. Critical paths have integration tests.

### 2.1 Unit Tests — Pattern Service

`tests/test_pattern_service.py`:

- `calculate_time_in_range()`: empty readings, all in range, all below, all above, mixed
- `detect_post_meal_spikes()`: no meals, meal with no spike, meal with spike, multiple meals
- `detect_overnight_hypoglycemia()`: no lows, single low, multiple nights
- `analyze_exercise_impact()`: no exercise, exercise with drop, exercise with rise
- Edge cases: single reading, duplicate timestamps, boundary values (exactly 70, 180 mg/dL)

### 2.2 Unit Tests — Safety Scaffold

`tests/ai/test_safety.py` — already exists, expand it:

- Add tests for `_check_policy_violations()` (dosing advice detection, treatment plan changes)
- Add tests for the assistant-source validation path
- Add tests for all severity levels and condition combinations

### 2.3 Unit Tests — LLM Service

`tests/test_llm_service.py`:

- `retrieve_context()`: verify correct DB queries, empty data handling
- `_build_system_prompt()`: verify prompt includes user profile, patterns, events, safety rules
- `_build_conversation_history()`: verify correct message formatting
- Provider fallback chain: OpenAI → Anthropic → OpenRouter → rule-based
- Mock all external HTTP calls (use `httpx.MockTransport` or `unittest.mock`)

### 2.4 Unit Tests — Agent Coordinator

`tests/test_agent_coordinator.py`:

- `delegate_task()` routes to correct agent
- `process_chat_message()` runs the full pipeline in order
- Safety violation short-circuits the pipeline
- Each agent's `handle()` delegates to the correct service

### 2.5 Integration Tests — API Endpoints

`tests/test_api_auth.py`: register, login, token refresh, protected endpoints
`tests/test_api_glucose.py`: CRUD, pagination, trend calculation
`tests/test_api_events.py`: CRUD for each event type (meal, insulin, exercise)
`tests/test_api_patterns.py`: pattern analysis endpoint, export endpoint

### 2.6 Integration Tests — Auth + Security

- JWT creation, decoding, expiration
- Password hashing and verification
- Protected endpoint access control
- Token refresh flow

**Phase 2 Acceptance Criteria:**
- [ ] 80%+ line coverage on `app/ai/safety.py`, `app/services/pattern_service.py`
- [ ] 70%+ line coverage on `app/services/llm_service.py`, `app/agents/coordinator.py`
- [ ] Integration tests for all CRUD endpoints
- [ ] All tests pass with `pytest -x` (no external dependencies needed)

---

## Phase 3: Data Ingestion

**Goal:** Real CGM data can flow into the system.

### 3.1 Dexcom OAuth Flow

`app/api/auth.py` + `app/services/dexcom_service.py`:

- Implement the OAuth callback endpoint (`/auth/dexcom/callback`)
- Store tokens in the `User` model (already has `dexcom_access_token`, `dexcom_refresh_token`, `dexcom_expires_at`)
- Implement token refresh logic
- Add a `/auth/dexcom/status` endpoint to check connection status

### 3.2 Nightscout Integration

`app/services/nightscout_service.py` — already implemented, needs:

- API route for configuring Nightscout URL/token per user
- Sync endpoint that calls `NightscoutService.sync_glucose_data()`
- Store Nightscout credentials in the `User` model (add columns if needed)

### 3.3 Background Sync

`app/services/sync_service.py` — needs to be created:

- Periodic task: every 5 minutes, sync CGM data for all connected users
- Use `asyncio` with a simple loop (no Celery dependency needed for MVP)
- On sync: fetch new readings → store → trigger pattern analysis
- Add a `/api/v1/sync/trigger` endpoint for manual sync

### 3.4 Food Database Integration

`app/food/providers/openfoodfacts.py` + `app/food/providers/usda.py`:

- Implement OpenFoodFacts API client (barcode search, name search)
- Implement USDA FoodData Central API client
- `FoodService.search()` queries personal DB first, then external providers
- Cache external results in the `Food` table

**Phase 3 Acceptance Criteria:**
- [ ] Dexcom OAuth flow works end-to-end (with real credentials)
- [ ] Nightscout sync works with a real Nightscout instance
- [ ] Background sync runs and populates glucose readings
- [ ] Food search returns results from external providers

---

## Phase 4: Frontend Integration

**Goal:** The React frontend talks to the real backend.

### 4.1 Auth Flow

`frontend/src/contexts/AuthContext.tsx`:

- Wire login/register to `POST /auth/login` and `POST /auth/register`
- Store JWT in `localStorage` (already there)
- Add token refresh logic
- Add logout (clear token + redirect)

### 4.2 Replace Demo Data with Real API Calls

For each hook (`useGlucose`, `useEvents`, `useFood`, `useExercise`, `useSleep`):

- Remove the demo data fallback (or keep it as dev-only mode)
- Call the real API endpoints with the stored JWT
- Handle loading/error states properly
- Add pagination support

### 4.3 Chat UI

`frontend/src/pages/Chat.tsx`:

- Wire to `POST /api/v1/chat` (blocking) or `/api/v1/chat/stream` (SSE)
- Display conversation history from `GET /api/v1/conversations/{id}/messages`
- Show loading state while waiting for response
- Handle safety escalation messages (show emergency resources)

### 4.4 Dashboard

`frontend/src/pages/Dashboard.tsx`:

- Show real glucose chart (last 24h) using `useGlucose`
- Show recent events from `useEvents`
- Show pattern summary (TIR, estimated A1C) from `GET /api/v1/patterns/tir`

**Phase 4 Acceptance Criteria:**
- [ ] User can register, log in, and see their data
- [ ] Chat sends real messages and displays real responses
- [ ] Dashboard shows real glucose chart and pattern summary
- [ ] All pages handle loading/error states

---

## Phase 5: Polish & Hardening

**Goal:** Production-ready quality.

### 5.1 Error Handling

- Consistent error responses across all endpoints (use the `ErrorResponse` model)
- Proper HTTP status codes (400, 401, 403, 404, 422, 500)
- Request validation with Pydantic (already mostly done)
- Global exception handler in `main.py` (already done)

### 5.2 Rate Limiting

- Add rate limiting to chat endpoint (prevent abuse)
- Add rate limiting to auth endpoints (prevent brute force)
- Use `slowapi` or similar

### 5.3 Input Validation

- Validate glucose values (0–600 mg/dL range)
- Validate carb values (0–500g)
- Validate insulin units (0–100)
- Validate timestamps (not in the future)

### 5.4 Documentation

- Update `SYSTEM.md` to reflect actual implementation
- Add API usage examples to `README.md`
- Add architecture decision records (`docs/adr/`) for key choices

### 5.5 Deployment

- Docker setup (already has `docker-compose.yml`)
- Health check endpoints (already has `/health`)
- Environment variable documentation
- Database migration guide

**Phase 5 Acceptance Criteria:**
- [ ] All endpoints return consistent error responses
- [ ] Rate limiting is active on sensitive endpoints
- [ ] Input validation rejects invalid data with clear messages
- [ ] Documentation matches actual behavior
- [ ] Docker setup works with `docker compose up`

---

## Priority Order & Dependencies

```
Phase 1 (Chat Pipeline) ──→ Phase 2 (Tests)
        │                        │
        ▼                        ▼
Phase 3 (Data Ingestion) ──→ Phase 4 (Frontend)
        │
        ▼
Phase 5 (Polish)
```

**Phase 1 is the critical path.** Without a working chat pipeline, the system is a CRUD app with a fancy architecture diagram. Phases 1+2 can be done in parallel by different people. Phase 3 depends on Phase 1 (sync needs the DB schema and agent pipeline). Phase 4 depends on Phases 1+3 (frontend needs working APIs and data). Phase 5 is continuous.

## Estimated Effort

| Phase | Scope | Estimated Work |
|-------|-------|---------------|
| Phase 1 | Wire agents, fix chat, fix RAG | ~40% of total effort |
| Phase 2 | Unit + integration tests | ~25% of total effort |
| Phase 3 | CGM sync, food providers | ~20% of total effort |
| Phase 4 | Frontend API integration | ~10% of total effort |
| Phase 5 | Polish, error handling, deploy | ~5% of total effort |

## Key Risks

1. **LLM provider availability.** Mitigation: rule-based fallback in Phase 1 so the pipeline works without API keys.
2. **Dexcom OAuth complexity.** Mitigation: Nightscout is simpler and can be implemented first.
3. **Test database setup.** Mitigation: use SQLite in-memory for unit tests, test Postgres for integration tests.
4. **Frontend-backend auth mismatch.** Mitigation: get the auth flow working first, then build features on top.
