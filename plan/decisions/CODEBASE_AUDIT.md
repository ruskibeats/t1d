# T1D Companion — Comprehensive Codebase Audit

**Date:** 2026-05-18  
**Scope:** Full backend + frontend + tests + infrastructure

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/TS)                         │
│  18 pages • ~4100 lines • React Router • TanStack Query            │
│  Pages: Dashboard, Glucose, Food, Exercise, Sleep, Events,         │
│         Patterns, Chat, Settings, Fasting, Measurements, Mood,     │
│         Water, Activity, Vitals, HealthMetrics, Login              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST API (25 routers)
┌──────────────────────────────▼──────────────────────────────────────┐
│                      BACKEND (FastAPI/Python)                       │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Agent        │  │ Services     │  │ API Layer                │  │
│  │ Coordinator  │──│              │──│                          │  │
│  │              │  │ LLMService   │  │ /auth (register,login,   │  │
│  │ 5 agents:    │  │ PatternSvc   │  │   dexcom OAuth,nightscout│  │
│  │ • Safety     │  │ DexcomSvc    │  │ /api/v1/glucose CRUD     │  │
│  │ • DataIngest │  │ NightscoutSvc│  │ /api/v1/events CRUD      │  │
│  │ • Pattern    │  │ MealSvc      │  │ /api/v1/patterns analyze │  │
│  │ • Conversation│ │ InsightsSvc  │  │ /api/v1/chat + stream    │  │
│  │ • Summary    │  │ HealthMetric │  │ /api/v1/insights         │  │
│  │              │  │   Service    │  │ /api/v1/metrics          │  │
│  │              │  │ SyncService  │  │ /api/v1/food,exercise,   │  │
│  │              │  │ MetricWriter │  │   sleep,fasting,mood,    │  │
│  │              │  │              │  │   water,measurements,    │  │
│  │              │  │              │  │   activity,vitals,       │  │
│  │              │  │              │  │   body_composition,      │  │
│  │              │  │              │  │   lifestyle,body_battery,│  │
│  │              │  │              │  │   environment,heart,     │  │
│  │              │  │              │  │   blood_pressure         │  │
│  │              │  │              │  │ /api/v1/garmin/webhook   │  │
│  │              │  │              │  │ /api/v1/fitbit,polar,    │  │
│  │              │  │              │  │   strava,withings        │  │
│  └─────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    DATA LAYER                                 │  │
│  │                                                               │  │
│  │  16 Domain Tables (dedicated CRUD per domain):               │  │
│  │  tbl_glucose_readings, tbl_context_events, tbl_conversations,│  │
│  │  tbl_conversation_messages, tbl_pattern_analyses,             │  │
│  │  exercise_entries, sleep_entries, food_entries, food,         │  │
│  │  fasting_entries, mood_entries, water_entries,                │  │
│  │  custom_measurements, environment_entries, heart_rate_entries,│  │
│  │  blood_pressure_entries, activity_entries, vital_entries,     │  │
│  │  body_composition_entries, lifestyle_entries,                 │  │
│  │  body_battery_entries                                         │  │
│  │                                                               │  │
│  │  Unified Graph Store (the "massive graph from day 1"):       │  │
│  │  health_metrics (StrEnum type + JSONB metadata)              │  │
│  │  health_daily_aggregates (pre-computed daily rollups)        │  │
│  │                                                               │  │
│  │  Dual-write: every domain create also writes health_metrics  │  │
│  │  via write_metric_if_present() helper                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. File Inventory

### Backend: 124 Python files

| Category | Count | Key Files |
|----------|-------|-----------|
| Domain packages (models/schemas/service) | 48 | 16 domains × 3 files each |
| API routers | 25 | auth, chat, glucose, events, patterns, insights, metrics, food, exercise, sleep, fasting, measurements, mood, water, activity, vitals, body_composition, lifestyle, body_battery, environment, heart, blood_pressure, garmin, fitbit, polar, strava, withings |
| Services | 10 | llm_service, pattern_service, dexcom_service, nightscout_service, meal_service, insights_service, sync_service, metric_writer, HealthMetricService, HealthAggregateService |
| AI/Agents | 5 | coordinator (5 agents), safety, llm, base, food_photo |
| Core infrastructure | 6 | main, config, database, security, errors, logging_config |
| DB layer | 2 | base, models |
| Ingestion providers | 5 | garmin, fitbit, polar, strava, withings |
| Migrations | ~20 | Alembic versions |

### Frontend: 40 TypeScript files

| Category | Count | Key Files |
|----------|-------|-----------|
| Pages | 18 | Dashboard, Glucose, FoodLog, ExerciseLog, SleepLog, Events, Patterns, Chat, Settings, Login, FastingLog, MeasurementsLog, MoodLog, WaterLog, ActivityPage, VitalsPage, HealthMetrics |
| Components | 8 | Layout, Button, Card, StatCard, GlucoseChart, QuickLog, RecentEvents |
| Hooks | 12 | useGlucose, useEvents, useFood, useExercise, useSleep, useFasting, useMeasurements, useMood, useWater, useHealthMetrics, useInsights |
| Contexts | 2 | AuthContext, GlucoseContext |
| Lib | 2 | demoData, utils |

### Tests: 29 test files, 297 passing

| Category | Tests | Files |
|----------|-------|-------|
| API integration | ~120 | test_api_auth, test_api_glucose, test_api_events, test_api_patterns, test_api_exercise, test_api_food, test_api_sleep, test_api_fasting, test_api_measurements, test_api_mood, test_api_water |
| Service unit | ~80 | test_pattern_service (37), test_llm_service (25), test_safety (30), test_dexcom_service, test_nightscout_service, test_food_providers |
| Chat pipeline | ~30 | test_chat_pipeline, test_chat_integration |
| Domain API | ~40 | test_heart, test_blood_pressure, test_activity, test_vitals, test_body_composition, test_lifestyle, test_body_battery, test_environment |
| Infrastructure | ~10 | test_dual_write |

---

## 3. What's Actually Built vs. What's Stubbed

### ✅ Fully Working

| Component | Evidence |
|-----------|----------|
| **Agent Coordinator** | All 5 agents wired to real services. `process_chat_message()` runs full pipeline: Safety → DataIngestion → Pattern → Conversation → Summary. Post-LLM safety validation included. |
| **LLM Service** | Multi-provider (OpenAI, Anthropic, OpenRouter, MiniMax) with automatic fallback chain. Rule-based fallback when no API key. RAG context retrieval from real DB. |
| **Pattern Service** | TIR, post-meal spikes, overnight hypoglycemia, exercise impact, delayed high-fat meals, correlations. All query real DB. |
| **Safety System** | Two-layer: SafetyAgent (emergency keywords + policy violations) + SafetyScaffold (condition-specific guardrails). Pre-LLM and post-LLM validation. |
| **Health Metrics Store** | `health_metrics` table with 40+ MetricType values. `HealthMetricService` with CRUD, batch ingest, dedup, aggregation. `HealthAggregateService` for daily rollups. |
| **Dual-Write** | `write_metric_if_present()` helper called from domain services. |
| **Dexcom Integration** | Full OAuth2 flow (auth URL, token exchange, refresh). Glucose data retrieval + sync with dedup. |
| **Nightscout Integration** | API client with connection testing, glucose sync. |
| **Food Providers** | OpenFoodFacts (name/barcode search, nutrient mapping). USDA FoodData Central. Unified search with local-first + external fallback + caching. |
| **Garmin Ingestion** | Full parser for activities, sleep, body composition. Webhook endpoint at `/api/v1/garmin/webhook`. |
| **Insights Service** | AI-driven pattern analysis. Pre-meal predictions based on historical data. |
| **Chat API** | `/api/v1/chat` (blocking), `/api/v1/chat/stream` (SSE word-by-word), `/api/v1/summarize-patterns`, `/api/v1/analyze-query`, `/api/v1/safety/check`. Full conversation CRUD. |
| **Auth** | JWT register/login/refresh/revoke. Dexcom OAuth callback. Nightscout config per user. |
| **Frontend** | 18 pages, all with real API hooks (useGlucose, useEvents, etc.). Auth context with JWT. React Query for data fetching. |
| **Tests** | 297 passing across 29 files. Mocked HTTP for external providers. |

### ⚠️ Partial / Needs Work

| Component | Status | Gap |
|-----------|--------|-----|
| **Fitbit/Polar/Strava/Withings** | Parsers exist, no OAuth routes | Only Garmin has a working webhook endpoint. Others have parse methods but no API routes or OAuth flows. |
| **Sync Service** | File exists, not wired into startup | `sync_service.py` has Celery task definitions but no Celery worker is started in `main.py` lifespan. |
| **Food Photo AI** | Agent file exists, not integrated | `app/ai/agents/food_photo.py` exists but isn't wired into the chat pipeline or meal logging flow. |
| **Frontend → Backend Auth** | Frontend has demo fallback | `AuthContext.tsx` has hardcoded `demo@t1d.com / demo123` bypass. Not connected to real JWT flow in production. |
| **Frontend pages** | All exist, some are thin | ActivityPage, VitalsPage, HealthMetricsPage exist but may be skeleton/demo data. |
| **Nightscout route** | Uses settings-level config | `glucose_ext.py` uses app-level Nightscout URL instead of per-user config. |
| **Streaming** | Pseudo-streaming | Chat stream endpoint does word-by-word SSE after full response is generated, not true token streaming from LLM. |

### ❌ Not Built

| Component | What's Missing |
|-----------|----------------|
| **Knowledge Graph edges** | `health_metrics` stores nodes but there's no edge/relationship table. Pattern detection uses raw SQL time-window queries, not graph traversal. |
| **Graph query layer** | No recursive CTE or graph traversal queries. No way to ask "what correlates with my 6pm spikes?" as a graph query. |
| **Celery workers** | Sync service defined but no worker process. No periodic background sync. |
| **CI/CD** | No GitHub Actions pipeline. |
| **Rate limiting** | TODO comment in auth.py, not implemented. |
| **Postgres test lane** | Tests run on SQLite. No Postgres integration test environment. |

---

## 4. The "Central Data Graph Feed Database" — Current State

This is the core of what you want to build. Here's what exists and what's missing:

### What Exists Today

```
Domain Tables (16)  ──dual-write──►  health_metrics (unified nodes)
                                          │
                                    health_daily_aggregates
                                          │
                              HealthMetricService (CRUD, query, aggregate)
```

- **`health_metrics` table**: Single polymorphic table with `MetricType` enum (40+ types), JSONB metadata, timestamp, source, provider_id. This IS the node store.
- **`health_daily_aggregates`**: Pre-computed daily rollups per metric type.
- **Dual-write**: Every domain create also writes a `HealthMetric` row via `write_metric_if_present()`.
- **Pattern detection**: Uses raw SQL time-window queries across `glucose_readings` and `context_events` — NOT graph traversal.

### What's Missing for a True Knowledge Graph

```
Today:  Nodes (health_metrics)  ←── no edges ──→  Nodes

Needed: Nodes (health_metrics)  ──edges──►  Nodes
              │
        Edge types:
        • meal → glucose_spike (confidence, time_delay)
        • exercise → glucose_drop (confidence, duration)
        • insulin → glucose_change (confidence, timing)
        • sleep → next_day_glucose (confidence)
        • high_fat_meal → delayed_spike (confidence, delay_hours)
        
        Graph queries:
        "What typically causes my 6pm spike?"
        "Show me all events correlated with overnight lows"
        "What's the chain: meal → insulin → glucose → exercise → glucose?"
```

**Specific gaps:**

1. **No edge table** — Need a `health_metric_edges` or `health_correlations` table with: `source_metric_id`, `target_metric_id`, `edge_type`, `confidence`, `time_delay`, `metadata`
2. **No graph traversal** — PatternService uses raw SQL. Need recursive CTE queries or a graph traversal layer.
3. **No correlation storage** — PatternAnalysis table exists but stores results as JSON blobs, not as queryable graph edges.
4. **No temporal reasoning** — Edges need time delays ("meal at 6pm → spike at 8pm") which the current schema doesn't capture.

---

## 5. Data Flow — How a Chat Message Actually Travels

```
User types "Why am I high at 6pm?"
    │
    ▼
POST /api/v1/chat
    │
    ▼
chat.py: save user message to DB
    │
    ▼
_build_context(): query last 24h glucose + 14d events + 14d patterns
    │
    ▼
AgentCoordinator.process_chat_message()
    │
    ├──► SafetyAgent.handle() — check emergency keywords + policy violations
    │       └── Uses compiled regex patterns (dosing advice, treatment changes)
    │
    ├──► DataIngestionAgent.handle() — get RAG context
    │       └── LLMService.retrieve_context() → queries glucose, events, patterns, user profile
    │
    ├──► PatternAgent.handle() — analyze patterns
    │       └── PatternService: TIR + spikes + overnight lows (raw SQL time-window queries)
    │
    ├──► ConversationAgent.handle() — generate response
    │       └── LLMService.generate_response() → builds system prompt with RAG context
    │           ├── Try primary provider (OpenRouter default)
    │           ├── Try fallback providers (provider_pool)
    │           └── Rule-based fallback (no API key)
    │
    ├──► Post-LLM SafetyAgent.handle() — validate assistant response
    │       └── Blocks dosing advice, treatment changes
    │
    └──► Return response + save to DB
```

---

## 6. Key Architectural Observations

### Strengths
1. **Clean separation**: Domain packages are well-isolated (models/schemas/service per domain)
2. **Safety-first**: Two-layer safety (pre + post LLM), emergency detection, no dosing advice
3. **Multi-provider LLM**: Graceful fallback chain with rule-based ultimate fallback
4. **Unified metrics store**: The `health_metrics` table is a solid foundation for the graph
5. **Test coverage**: 297 tests, external APIs properly mocked
6. **Dual-write pattern**: Domain tables + unified store keeps both operational and analytical paths

### Weaknesses
1. **No graph edges**: The knowledge graph is a flat node store without relationships
2. **Pattern detection is SQL-heavy**: Time-window queries instead of graph traversal
3. **No background sync**: Celery tasks defined but not running
4. **Frontend-backend auth gap**: Demo mode hardcoded, not production-ready
5. **Insights service has a bug**: `InsightsService.generate_all_insights()` is referenced in the API router but the method is actually `generate_insights()` — mismatch
6. **Food photo agent exists but isn't wired in**
7. **No rate limiting, no CI/CD**

---

## 7. Recommended Priority for "Central Data Graph Feed Database"

If the goal is to build a proper knowledge graph that all data feeds into:

### Phase A: Graph Foundation
1. Create `health_metric_edges` table (source_id, target_id, edge_type, confidence, time_delay, metadata)
2. Write edge-creation logic in PatternService (when a spike is detected after a meal, create an edge)
3. Add graph traversal queries (recursive CTEs for "what causes X?")

### Phase B: Graph-Powered AI
4. Feed graph subgraphs into LLM context instead of flat data rows
5. Rewrite PatternService to use graph traversal instead of raw SQL time-windows
6. Add temporal reasoning (time-delayed edges)

### Phase C: Graph-Powered Features
7. "What if" queries ("What if I eat pizza at 6pm?")
8. Causal chain visualization in frontend
9. Personal pattern knowledge graph that grows over time
