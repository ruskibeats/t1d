# T1D Companion — Next Plan: Internal Alpha → Production-Hardened Backend

## Executive Summary

The current backend is **demo-ready / internal-alpha ready**:

- ✅ Multi-agent chat pipeline is real and reachable through `app.state.coordinator`
- ✅ Safety scaffold exists and is tested
- ✅ LLM fallback works without API keys
- ✅ Pattern analytics are implemented and tested
- ✅ Dexcom/Nightscout endpoints exist
- ✅ Food providers exist
- ✅ Final review passed
- ✅ Focused suite: `101 passed`

This next plan turns the solution from **working MVP** into **trustworthy backend foundation** by focusing on:

1. Real DB-backed end-to-end tests
2. Post-LLM safety validation
3. External provider mock tests
4. Auth/API integration coverage
5. Test infrastructure hardening
6. Warning cleanup
7. Low-cost subagent superteam execution

The operating model is still: **high-energy, subagent-heavy, reviewer/fixer loops, zero/low-cost models first**.

---

## Guiding Principles

### 1. Medical safety beats feature speed
This is an educational diabetes companion, not a medical device. Any assistant response touching glucose, insulin, meals, or exercise must avoid treatment directives and dosing advice.

### 2. Prove real paths, not just units
The current tests are good but still mostly unit-level. The next phase must exercise real API routes, real DB persistence, and real coordinator flow.

### 3. External APIs must be fake in tests
Dexcom, Nightscout, OpenFoodFacts, and USDA need mocked HTTP tests. No test should hit the network.

### 4. Subagents do implementation; parent coordinates
The parent session owns scope, sequencing, review synthesis, and conflict resolution. Subagents own bounded work packages.

### 5. Cheap/free model rotation only
Known-good default:

```text
openrouter/deepseek/deepseek-v4-flash
```

Backup candidates:

```text
openrouter/owl-alpha
openrouter/openai/gpt-4o-mini  # cheap fallback, if available
```

Avoid based on known failures:

```text
openai-codex                 # model not found
openai/gpt-5.5               # no OpenAI API key
bare deepseek/...            # no DeepSeek API key
openai/gpt-oss-120b:free     # reasoning endpoint issue
minimax/minimax-m2.5:free    # reasoning endpoint issue
```

---

## Current Highest-Risk Gaps

| Risk | Why it matters | Priority |
|---|---|---|
| No true DB-backed `/chat` endpoint test | Chat can regress while unit tests stay green | P0 |
| No post-LLM safety validation | Unsafe generated text could be saved/returned | P0 |
| Coordinator SafetyAgent duplicates safety logic | Safety rules can drift from `SafetyScaffold` | P0 |
| Food provider method collision / recursion risk | Food search may silently fail or recurse | P1 |
| Dexcom/Nightscout untested with mocked API responses | Data ingestion can break invisibly | P1 |
| SQLite fixture only creates core tables | API integration tests for domain modules may fail | P1 |
| 450+ warnings | Warning noise hides real regressions | P2 |
| No Postgres integration test lane | JSONB/ENUM behavior not truly verified | P2 |

---

# Wave Plan

## Wave 3A — Safety and Chat E2E Lockdown

**Goal:** Make the conversational path clinically safer and prove it works through the real HTTP/API/DB path.

### Work Package A1: Post-LLM Safety Validation

**Files:**

- `app/agents/coordinator.py`
- `app/api/chat.py`
- `tests/test_chat_pipeline.py`
- optional: `tests/test_chat_integration.py`

**Changes:**

1. Make `SafetyAgent.handle()` delegate to `SafetyScaffold.validate()` instead of duplicating emergency keyword logic.
2. After `ConversationAgent` produces an assistant response, validate it with:

```python
SafetyScaffold.validate(response_text, {"source": "assistant"})
```

3. If unsafe:
   - do **not** return or save unsafe content
   - return a safe educational fallback
   - include healthcare-provider disclaimer
   - log/audit the safety event

4. Add tests:
   - LLM returns `"You should take 5 units"` → response is blocked/replaced
   - LLM returns treatment-change advice → blocked/replaced
   - safe educational response → passes
   - emergency user input → short-circuits before LLM

**Acceptance:**

- 4+ new safety/chat tests pass
- No dosing advice can be returned from mocked LLM output
- `SafetyAgent` no longer maintains a separate keyword dictionary

**Subagent:** `phase2-safety-llm-tests-v2` or `worker`

---

### Work Package A2: DB-backed Chat Endpoint Integration Tests

**Files:**

- `tests/test_chat_integration.py` new
- `tests/conftest.py` if needed

**Tests:**

1. `POST /api/v1/chat` with authenticated test user:
   - creates/saves user message
   - calls coordinator
   - returns assistant response
   - saves assistant message

2. seeded glucose + meal context:
   - insert `GlucoseReading`
   - insert meal `ContextEvent`
   - ask pattern question
   - verify response/context includes pattern summary

3. existing conversation:
   - pass `conversation_id`
   - verify message count increases

4. coordinator unavailable path:
   - no `app.state.coordinator`
   - returns graceful assistant-unavailable message

5. streaming route:
   - validates SSE chunks
   - uses real `ai_message.id`

**Acceptance:**

- 5+ DB-backed chat endpoint tests pass
- Tests use local DB only
- No external LLM calls

**Subagent:** `phase1-integration-tests` or `worker`

---

## Wave 3B — Auth and Provider Test Foundation

**Goal:** Add reliable integration tests around authentication and external-provider boundaries.

### Work Package B1: Auth API Integration Tests

**Files:**

- `tests/test_api_auth.py` new

**Tests:**

- register success
- duplicate email fails
- login success returns JWT
- login wrong password fails
- `/auth/me` requires token
- `/auth/me` returns active user
- patch `/auth/me` updates profile
- Dexcom callback mocks token exchange and stores tokens

**Acceptance:**

- 8+ auth tests pass
- no real external calls
- password hashing works or is safely monkeypatched for speed

**Subagent:** `worker`

---

### Work Package B2: HTTP Mocking Utility

**Files:**

- `pyproject.toml`
- `tests/conftest.py`

**Decision:** Prefer **pytest-httpx** unless dependency policy says no.

Add dev dependency:

```toml
pytest-httpx>=0.30.0
```

If avoiding dependencies, use monkeypatch around `httpx.AsyncClient` directly.

**Acceptance:**

- External-provider tests can mock HTTP without network
- CI/test docs mention no network tests

**Subagent:** parent or `worker`

---

## Wave 3C — Dexcom/Nightscout Hardening

**Goal:** Real CGM ingestion code becomes test-protected.

### Work Package C1: Dexcom Service Tests

**Files:**

- `tests/test_dexcom_service.py` new

**Tests:**

- authorization URL includes expected params
- exchange code → token object
- refresh token → new token object
- glucose API response → normalized readings
- sync inserts readings
- duplicate timestamp/source skipped
- API error raises/returns graceful failure as designed
- expired token refresh path

**Acceptance:**

- 8+ Dexcom tests pass
- mocked HTTP only

**Subagent:** `phase3-dexcom-nightscout-v2` or `worker`

---

### Work Package C2: Nightscout Service + Route Tests

**Files:**

- `tests/test_nightscout_service.py` new
- `tests/test_api_nightscout.py` optional
- `app/api/glucose_ext.py`

**Known issue to fix:**

`app/api/glucose_ext.py` appears to use settings-level Nightscout URL/token instead of user-level `user.nightscout_url`. Fix route behavior so user configuration is authoritative.

**Tests:**

- `_test_connection` success/failure
- entries/sgv response normalization
- sync inserts readings
- duplicate readings skipped
- route rejects unconfigured user
- route uses user-level Nightscout URL/token

**Acceptance:**

- 8+ Nightscout tests pass
- user-level config is verified
- no real HTTP calls

**Subagent:** `phase3-dexcom-nightscout-v2` or `worker`

---

## Wave 3D — Food Provider Hardening

**Goal:** Food provider code is tested and the suspected `search_foods` method collision is fixed.

### Work Package D1: Fix FoodService Search Shape

**Files:**

- `app/food/service.py`
- `tests/test_food_providers.py`

**Known issue:**

Scout found `FoodService.search_foods` defined twice; the second overrides the first and may call itself recursively when trying to search local DB.

**Fix direction:**

Split into explicit methods:

```python
_search_local_foods(...)
search_foods(...)  # orchestrates local → OpenFoodFacts → USDA
search_all_providers(...)
```

**Acceptance:**

- local DB search does not recurse
- local hit avoids external calls
- external miss caches result when appropriate

---

### Work Package D2: Provider Mock Tests

**Files:**

- `tests/test_food_providers.py`

**Tests:**

OpenFoodFacts:

- name search parses products
- barcode search parses product
- nutriments mapped to carbs/protein/fat/calories
- HTTP 429 → empty result
- malformed response → empty result

USDA:

- name search parses foods
- nutrient IDs mapped correctly
- no API key → empty result
- HTTP error → empty result

FoodService:

- local hit
- local miss → provider hit → cache
- all providers fail → empty result

**Acceptance:**

- 12+ food tests pass
- no real HTTP calls

**Subagent:** `phase3-food-providers-v2` or `worker`

---

## Wave 3E — Pattern/API Thin Integration

**Goal:** PatternService is already well-tested; now verify API wrappers.

**Files:**

- `tests/test_api_patterns.py` new

**Tests:**

- `/api/v1/patterns/tir` with seeded readings
- `/api/v1/patterns/spikes` with meal + glucose spike
- `/api/v1/patterns/overnight` with overnight low
- empty-data response is graceful
- unauthorized requests fail

**Acceptance:**

- 5+ pattern API tests pass

**Subagent:** `worker`

---

## Wave 3F — Test Infrastructure and Warning Cleanup

**Goal:** Make tests easier to trust and prepare for CI.

### Work Package F1: Warning Cleanup

**Files likely involved:**

- `app/core/logging_config.py`
- `app/db/base.py`
- `app/config.py`
- `app/*/schemas.py`
- selected `datetime.utcnow()` sites in non-API files

**Targets:**

- Pydantic V2 `class Config` → `model_config = ConfigDict(...)`
- SQLAlchemy `declarative_base` deprecation
- `datetime.utcnow()` deprecations

**Acceptance:**

- full focused test suite still passes
- warning count reduced by at least 50%
- no domain behavior changes

**Subagent:** `worker` or purpose-built `fixer-warnings`

---

### Work Package F2: Postgres Test Lane

**Files:**

- `tests/conftest.py`
- `docker-compose.test.yml` new
- `README.md` or `DEVELOPMENT.md`

**Add:**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/t1d_test
```

Test behavior:

- default fast lane can stay SQLite subset
- integration lane can use Postgres and full metadata

**Acceptance:**

- `pytest tests/ -q` still works locally
- documented Postgres test command exists
- full metadata can be tested outside SQLite workaround

**Subagent:** `worker`

---

## Wave 3G — LLM Provider Rotation

**Goal:** Configure resilient cheap/free provider rotation while preserving rule-based fallback.

**Files:**

- `app/services/llm_service.py`
- `tests/test_llm_service.py`
- `app/config.py`

**Design:**

- Keep primary configured provider behavior
- Add optional provider/model pool from settings/env
- On provider failure/rate-limit/no-key, try next provider
- If all fail, use rule-based fallback

Example env:

```bash
LLM_PROVIDER_POOL=openrouter/deepseek/deepseek-v4-flash,openrouter/owl-alpha
```

**Acceptance:**

- provider rotation tests pass
- no external calls in tests
- rule-based fallback remains final safety net

**Subagent:** `phase1-llm-fallback` or `worker`

---

# Execution Strategy: High-Energy Superteam

## Launch Rule

Do not launch implementation subagents until human approval.

Once approved, launch independent work packages in parallel:

```text
Batch 1 — P0/P1 safety + proof
  A1: Post-LLM safety validation
  A2: DB-backed chat integration tests
  B1: Auth API tests

Review/Fix 1
  reviewer-wave3
  fixer-wave3 if needed

Batch 2 — External data boundaries
  C1: Dexcom tests
  C2: Nightscout tests + user-level URL fix
  D1/D2: Food service/provider tests + search fix

Review/Fix 2
  reviewer-wave4
  fixer-wave4 if needed

Batch 3 — Infra polish
  E: Pattern API tests
  F1: Warning cleanup
  F2: Postgres test lane
  G: LLM provider rotation

Review/Fix 3
  reviewer-wave5
  fixer-wave5 if needed
```

## Suggested Subagent Model Config

Primary:

```json
{
  "model": "openrouter/deepseek/deepseek-v4-flash",
  "context": "fork",
  "async": true
}
```

Fallback:

```json
{
  "model": "openrouter/owl-alpha",
  "context": "fork",
  "async": true
}
```

Avoid generic agents that lack tools in this environment unless verified. In the last planning run:

- `planner` failed: `Tool bash not found`
- `reviewer` failed: `Tool todo not found`
- `scout` succeeded

Prefer project agents or `worker` with explicit tool expectations.

---

# New Agent Definitions To Create

Recommended new `.pi/agents/` files:

| Agent | Purpose |
|---|---|
| `wave3-post-llm-safety.md` | Add post-LLM safety validation and tests |
| `wave3-chat-e2e-tests.md` | DB-backed authenticated chat endpoint tests |
| `wave3-auth-api-tests.md` | Auth/register/login/protected endpoint tests |
| `wave4-cgm-provider-tests.md` | Dexcom + Nightscout service/route tests |
| `wave4-food-provider-tests.md` | Food provider tests and search service cleanup |
| `wave5-warning-cleanup.md` | Pydantic/SQLAlchemy/datetime warning cleanup |
| `wave5-postgres-test-lane.md` | Postgres integration test lane |
| `wave5-llm-provider-rotation.md` | Provider pool + fallback tests |
| `reviewer-wave3.md` | Review Batch 1 |
| `reviewer-wave4.md` | Review Batch 2 |
| `reviewer-wave5.md` | Review Batch 3 |
| `fixer-wave3.md` | Fix reviewer-wave3 issues |
| `fixer-wave4.md` | Fix reviewer-wave4 issues |
| `fixer-wave5.md` | Fix reviewer-wave5 issues |

---

# Acceptance Criteria For This Whole Plan

By the end:

- [ ] 130+ total tests passing
- [ ] authenticated DB-backed `/api/v1/chat` tests exist
- [ ] post-LLM safety blocks unsafe assistant content
- [ ] coordinator SafetyAgent delegates to `SafetyScaffold`
- [ ] Dexcom service tests use mocked HTTP
- [ ] Nightscout service/route tests use mocked HTTP
- [ ] Food provider tests use mocked HTTP
- [ ] FoodService local/external search has no method collision or recursion
- [ ] Nightscout sync uses user-level config where appropriate
- [ ] warning count reduced materially
- [ ] optional Postgres integration test lane documented
- [ ] final reviewer reports no production blockers

---

# Grill-Me Questions Before Launch

I can proceed with these assumptions, but these are the decisions worth grilling before execution:

1. **Post-LLM safety behavior:** Should unsafe assistant text be replaced with a generic safe response, or should it be rewritten into a safe educational response?
2. **HTTP mocking dependency:** Are we allowed to add `pytest-httpx` to dev dependencies, or should tests monkeypatch `httpx.AsyncClient` manually?
3. **Test DB lane:** Do you want Postgres test infra now, or after we add provider/API tests?
4. **Food provider caching:** Should external provider results always be cached locally, or only when the user selects/logs the food?
5. **Streaming semantics:** Is current pseudo-streaming acceptable for MVP, or do we need true provider token streaming soon?
6. **Subagent aggressiveness:** For Batch 1, do you want 3 parallel agents immediately, or a smaller 2-agent first strike to avoid conflicts?

My recommendation: **approve Batch 1 with 3 parallel agents** — post-LLM safety, DB-backed chat tests, and auth API tests. They are high-value, mostly disjoint, and give us the strongest safety net for everything else.
