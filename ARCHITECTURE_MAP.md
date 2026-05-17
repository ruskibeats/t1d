# T1D Companion — Architecture Map

124 Python backend files · 40 TypeScript frontend files · 25 API routers

## Layer 1: Presentation (React)

```
frontend/src/
├── App.tsx                    ← Routes (14 pages)
├── pages/
│   ├── Dashboard.tsx          ← Glucose curve + stats + QuickLog + RecentEvents
│   ├── Glucose.tsx            ← CGM table + trend stats
│   ├── FoodLog.tsx            ← Food search + meal logging + daily totals
│   ├── ExerciseLog.tsx        ← Exercise sessions + weekly stats
│   ├── SleepLog.tsx           ← Sleep duration + quality + stage breakdown
│   ├── Events.tsx             ← All context events (meals/insulin/exercise/…)
│   ├── Patterns.tsx           ← TIR/grade + spikes + overnight + exercise impact
│   ├── Chat.tsx               ← LLM chat + streaming + conversation history + spike predictor
│   ├── Settings.tsx           ← Profile save + Nightscout config + Dexcom OAuth
│   ├── Login.tsx              ← Auth with demo fallback
│   ├── FastingLog.tsx         ← Fasting periods + streak + daily active
│   ├── MeasurementsLog.tsx    ← Custom metrics (weight/BF%/BMI) + body composition
│   ├── MoodLog.tsx            ← Mood score (1–10) + notes
│   ├── WaterLog.tsx           ← Water intake + quick-add buttons + daily target
│   ├── VitalsPage.tsx         ← Heart rate + BP + SpO2 + body battery
│   ├── ActivityPage.tsx       ← Steps + distance + floors climbed
│   └── HealthMetrics.tsx      ← Unified cross-domain metrics dashboard
├── components/
│   ├── Layout.tsx             ← Sidebar nav (14 items) + brand + safety badge
│   ├── dashboard/             ← QuickLog + RecentEvents widgets
│   ├── charts/                ← GlucoseChart (recharts)
│   └── ui/                    ← Button, Card, StatCard
├── hooks/
│   ├── useGlucose.ts          ← GET/POST /api/v1/glucose
│   ├── useFood.ts             ← GET/POST /api/v1/food with search
│   ├── useExercise.ts         ← GET/POST /api/v1/exercise
│   ├── useSleep.ts            ← GET/POST /api/v1/sleep
│   ├── useEvents.ts           ← GET/POST /api/v1/events
│   ├── useHealthMetrics.ts    ← GET /api/v1/metrics
│   ├── useFasting.ts          ← GET/POST /api/v1/fasting
│   ├── useMeasurements.ts     ← GET/POST /api/v1/measurements
│   ├── useMood.ts             ← GET/POST/DELETE /api/v1/mood
│   └── useWater.ts            ← GET/POST /api/v1/water
├── contexts/
│   └── AuthContext.tsx        ← Login/logout/token management + demo user
├── lib/
│   └── demoData.ts            ← Demo glucose + events + sleep (kept for dev)
└── types/
    └── index.ts               ← TypeScript interfaces
```

**Key flow**: Every hook → `axios` call → API → service → DB model. Auth token via `axios.defaults.headers.common['Authorization']`.

## Layer 2: API (FastAPI Routers)

```
app/api/                       ← 25 routers mounted in app/main.py
├── auth.py                    ← POST /auth/register, /auth/login, PATCH /auth/me
├── chat.py                    ← POST /api/v1/chat, /chat/stream, GET /conversations
├── glucose.py                 ← CRUD + stats + trends for glucose_readings
├── glucose_ext.py             ← Dexcom/Nightscout sync triggers
├── events.py                  ← CRUD for context_events
├── patterns.py                ← Pattern analysis: TIR, spikes, overnight, exercise
├── users.py                   ← Profile + Nightscout config/sync
├── food.py                    ← Food search + entries CRUD
├── exercise.py                ← Exercise sessions + sets CRUD
├── sleep.py                   ← Sleep entries + stages CRUD
├── fasting.py                 ← Fasting periods CRUD
├── measurements.py            ← Custom measurements CRUD
├── mood.py                    ← Mood entries CRUD
├── water.py                   ← Water entries CRUD
├── heart.py                   ← Heart rate entries CRUD
├── blood_pressure.py          ← BP entries CRUD
├── activity.py                ← Steps/distance/floors CRUD
├── vitals.py                  ← SpO2/respiratory/temperature CRUD
├── body_composition.py        ← Weight/BF%/BMI/lean/waist CRUD
├── body_battery.py            ← Body battery CRUD
├── lifestyle.py               ← Stress/energy/caffeine CRUD
├── environment.py             ← Temperature/humidity/altitude CRUD
├── metrics.py                 ← Unified health_metrics query endpoint
├── fitbit.py                  ← Fitbit OAuth + webhook (mounted)
├── garmin.py                  ← Garmin webhook + sync (mounted)
├── polar.py                   ← Polar sync (mounted)
├── strava.py                  ← Strava OAuth + sync (mounted)
└── withings.py                ← Withings webhook (mounted)
```

**Key flow**: Every router → `Depends(require_active_user)` → `Depends(get_db)` → service → model.

## Layer 3: Agent Orchestration

```
app/agents/
└── coordinator.py             ← AgentCoordinator + 5 agents
    ├── SafetyAgent            ← Emergency keywords + policy violation check
    ├── DataIngestionAgent     ← Fetches glucose + events + builds RAG context
    ├── PatternAgent           ← Calls PatternService for TIR/spikes/overnight
    ├── ConversationAgent      ← Calls LLMService with RAG context + history
    └── SummaryAgent           ← Generates clinic-ready text summaries

app/ai/
└── safety.py                  ← SafetyScaffold: condition-specific guardrails
    ├── _DIABETES_EMERGENCY_KEYWORDS
    ├── _POLICY_VIOLATION_PATTERNS (dosing advice regex)
    └── validate()             ← Checks both user input AND LLM output
```

**Key flow**: `POST /api/v1/chat` → `AgentCoordinator.process_chat_message()` → SafetyAgent → DataIngestionAgent → PatternAgent → ConversationAgent → post-LLM safety check → response.

## Layer 4: Services (Business Logic)

```
app/services/
├── llm_service.py             ← Multi-provider LLM (OpenRouter) + RAG context + fallback
├── pattern_service.py         ← TIR, spike detection, overnight hypo, exercise impact
├── dexcom_service.py          ← Dexcom OAuth2 + glucose sync
├── nightscout_service.py      ← Nightscout API + glucose sync
├── meal_service.py            ← Meal planning + nutritional analysis
├── sync_service.py            ← Background sync orchestrator
└── metric_writer.py           ← Dual-write helper: domain → health_metrics
```

Every command:

## Layer 5: Data (SQLAlchemy Models)

```
app/db/
├── base.py                    ← SQLAlchemy declarative Base
├── models.py                  ← User, GlucoseReading, ContextEvent, Conversation, ConversationMessage, PatternAnalysis
│   + all relationship back_populates for every domain model
│
app/<domain>/models.py         ← One dedicated table per domain:
│   exercise/                  → exercise_entries, exercise_entry_sets
│   food/                      → foods, food_entries
│   sleep/                     → sleep_entries, sleep_stages
│   fasting/                   → fasting_entries
│   measurements/              → custom_measurements
│   mood/                      → mood_entries
│   water/                     → water_entries
│   heart/                     → heart_rate_entries
│   blood_pressure/            → blood_pressure_entries
│   activity/                  → activity_entries
│   vitals/                    → vital_entries
│   body_composition/          → body_composition_entries
│   body_battery/              → body_battery_entries
│   lifestyle/                 → lifestyle_entries
│   environment/               → environment_entries
│
app/metrics/
├── types.py                   ← MetricType StrEnum (50 types)
├── models.py                  → health_metrics (polymorphic), health_daily_aggregates
├── schemas.py                 ← HealthMetricCreate/Response/Query/Summary
└── service.py                 ← CRUD + batch + aggregation
```

**Key flow**: Every domain `create()` → writes domain table row → calls `write_metric_if_present()` → writes `HealthMetric` row. The unified `health_metrics` table is the canonical cross-domain store for the AI pipeline and HealthMetricsPage dashboard.

## Complete Write Path (Example: Exercise)

```
User clicks "Log exercise" on ExerciseLog.tsx
  → useExercise.createEntry(post body)
    → axios.post('/api/v1/exercise', data)
      → exercise router: POST /api/v1/exercise
        → ExerciseService(db).create_entry(user.id, data)
          → ExerciseEntry(user_id=user_id, ...) insert → exercise_entries
          → write_metric_if_present(MetricType.EXERCISE_MINUTES, ...) → health_metrics
          → write_metric_if_present(MetricType.EXERCISE_CALORIES, ...) → health_metrics
```

## Complete Read Path (Example: Health Dashboard)

```
User views HealthMetricsPage.tsx
  → useHealthMetrics.fetchMetrics('3d')
    → axios.get('/api/v1/metrics?start=...&end=...')
      → metrics router: GET /api/v1/metrics
        → HealthMetricService.query(user_id, params)
          → SELECT * FROM health_metrics WHERE user_id=? AND measured_at BETWEEN ? AND ?
```

## Complete Chat Path

```
User types "Why did I spike after pizza?"
  → Chat.tsx: fetch POST /api/v1/chat/stream (SSE)
    → chat.py: chat_stream()
      → _build_context() — glucose readings + context events
      → AgentCoordinator.process_chat_message()
        → SafetyAgent.handle() — check emergency keywords → safe
        → DataIngestionAgent.handle() — fetch glucose + events + pattern summary
        → PatternAgent.handle() — run TIR + spike detection
        → ConversationAgent.handle() — RAG context + LLM prompt
        → SafetyScaffold.validate(response) — post-LLM check
      → stream SSE chunks back to frontend
```

## Ingest Providers Pipeline

```
External service hits webhook (e.g., Garmin POST /api/v1/garmin/webhook)
  → garmin.py: route handler
    → app/ingestion/garmin.py: parse webhook payload
      → writes to domain table (e.g., activity_entries)
      → writes to health_metrics
```
