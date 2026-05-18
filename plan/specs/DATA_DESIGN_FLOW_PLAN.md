# T1D Companion — Data Design, Flow, Graph, ML/AI Plan

**Date:** 2026-05-18  
**Perspective:** Data engineering + applied ML/AI + health-safety architecture  
**Current foundation:** `health_metrics` node table, `health_metric_edges` graph table, 16 domain packages, 304 tests passing  
**Goal:** Build a central personal health data graph that collects multi-source data, creates explainable relationships, powers pattern detection, and feeds safe AI/RAG experiences.

---

## 1. Executive Summary

The project is moving from a CRUD + analytics app into a **personal health knowledge graph** for Type 1 Diabetes.

The core idea:

```text
All health/life data feeds into one central graph.

Domain tables keep operational detail.
health_metrics stores normalized facts as graph nodes.
health_metric_edges stores detected relationships as graph edges.
Pattern + ML services create evidence.
LLM/RAG uses the graph to explain patterns safely.
Frontend surfaces the graph as calm, useful observations.
```

This makes the product more than a dashboard. It becomes a memory system that can answer:

- “What usually happens when I eat pizza?”
- “Why am I often high around 6pm?”
- “What changed before my overnight lows?”
- “Does exercise after lunch make me lower later?”
- “Which patterns are worth taking to my diabetes review?”

The graph is **observational**, not prescriptive. It must never become a dosing engine.

---

## 2. Current Data Architecture

### Existing operational tables

The app currently has dedicated domain tables for rich CRUD and domain-specific UI:

- Users/auth/profile
- Glucose readings
- Context events
- Conversations/messages
- Pattern analyses
- Food / food entries
- Exercise
- Sleep
- Measurements
- Fasting
- Mood
- Water
- Environment
- Heart rate
- Blood pressure
- Activity
- Vitals
- Body composition
- Lifestyle
- Body battery

### Existing central node table

`health_metrics` is the normalized polymorphic fact table.

Each row is one graph node:

```text
user_id
metric type
value
unit
measured_at / ended_at
source
provider_id
metadata
```

Examples:

```text
BLOOD_GLUCOSE 224 mg/dL at 20:10 from dexcom
CARBS 80 g at 18:05 from manual food log
EXERCISE_MINUTES 45 minutes at 13:00 from garmin
SLEEP_HOURS 7.2 hours from apple_health
HEART_RATE 48 bpm at 03:12 from garmin
```

### New graph edge table

`health_metric_edges` stores relationships between nodes.

Each row is one edge:

```text
source_metric_id → target_metric_id
edge_type
confidence
time_delay_seconds
algorithm
evidence JSON
```

Example:

```text
CARBS metric → BLOOD_GLUCOSE metric
edge_type = meal_to_glucose_spike
confidence = 0.82
time_delay_seconds = 7200
evidence = { food_name, carbs, baseline, peak, rise, severity }
```

---

## 3. Data Engineering Principles

### 3.1 Keep domain tables and graph table

Do not replace domain tables with the graph.

Use both:

| Layer | Purpose |
|---|---|
| Domain tables | CRUD, forms, validation, UI detail, exact user logs |
| `health_metrics` | unified normalized time-series facts |
| `health_metric_edges` | relationships, evidence, explanations |
| Aggregates/features | fast dashboards, model features, trend summaries |

### 3.2 Ingest once, normalize always

Every provider/raw input should be transformed into canonical `HealthMetricCreate` records.

### 3.3 Prefer evidence over prediction early

Start with rule/statistical relationships because they are auditable and safe.

ML comes after enough data exists.

### 3.4 Graph edges are evidence, not medical advice

Edges answer:

```text
“What happened before/after this?”
“What relationships recur?”
“What might be worth reviewing?”
```

Edges must not answer:

```text
“How much insulin should I take?”
“Should I change treatment?”
```

### 3.5 Confidence must be explainable

Every confidence score should be traceable to simple evidence:

- number of repeated occurrences
- magnitude of glucose change
- timing consistency
- data completeness
- recency
- signal quality/source reliability

### 3.6 Models propose; our pipeline decides

Hosted or self-hosted AI models are replaceable inference steps inside our ingestion pipeline. They do not own product logic, safety logic, nutrition truth, graph writes, or user-facing explanations.

For photo meal ingest specifically:

```text
image → vision model proposal → our validation/cleaning → user confirmation
      → nutrition mapping → domain tables + health_metrics → graph edges/RAG
```

Our code owns:

- confidence thresholds and max item limits
- JSON/schema validation
- label normalization and food database mapping
- macro/carbohydrate calculation after confirmation
- event grouping
- graph writes
- provenance
- safe copy and RAG explanation

The vision model’s job is narrow: suggest food regions and labels.

---

## 4. Data Sources and Collection Plan

## 4.1 Core T1D Data

### Glucose / CGM

**Sources:**

- Dexcom OAuth/API
- Nightscout API
- Manual fingerstick entry
- Future: Apple Health glucose if available

**Collected fields:**

- timestamp
- glucose value
- units
- trend direction
- trend rate if available
- source/device
- raw payload

**Writes:**

- `tbl_glucose_readings`
- `health_metrics` as `BLOOD_GLUCOSE`
- optional `CGM_TREND`

**Primary uses:**

- TIR
- spikes
- lows
- variability
- pattern targets for graph edges

---

### Meals / Nutrition

**Sources:**

- Manual food logging
- Barcode scan
- OpenFoodFacts
- USDA FoodData Central
- Photo ingest via open-source detection/segmentation + human confirmation
- Future: fine-tuned food/ingredient segmentation

**Photo-ingest strategy:**

Photo ingest is a vision inference step inside the broader meal ingestion pipeline. It is not a truth engine and it is not the whole feature. It produces provisional item proposals that must flow through validation and human confirmation before becoming food logs, metrics, or graph data.

The problem splits into three layers:

1. **Food classification** — “this looks like a burger.” Useful but insufficient.
2. **Food detection / segmentation** — “there are fries here and a burger here.” Best match for overlay-based meal review.
3. **Nutrition estimation** — “roughly 42g carbs.” Highest uncertainty; should happen after user confirmation and food database lookup.

Two implementation options:

| Option | Best for | Tradeoff |
|---|---|---|
| Hosted vision model | Fastest v1 | Less control, API cost, must validate hard |
| Self-hosted OSS model | More control and privacy | More infrastructure, model serving, preprocessing/postprocessing |

Hosted v1 flow:

```text
FastAPI upload → hosted vision call with strict JSON contract
               → validate/clamp proposals
               → user review/edit
               → nutrition lookup
               → graph write after confirmation
```

Self-hosted future flow:

```text
FastAPI upload → queue job → Python worker with FoodSAM/YOLO/etc.
               → preprocessing/postprocessing/NMS/thresholding
               → same proposal contract
               → same confirmation/nutrition/graph path
```

The backend should hide both behind one swappable interface:

```python
analyze_meal_image(image) -> MealImageAnalysisProposal
```

Recommended open-source direction:

| Candidate | Use | Notes |
|---|---|---|
| FoodSAM | Food segmentation | Best fit for image overlays / instance segmentation |
| FoodInsSeg | Ingredient-level masks/dataset | Useful for fine-tuning or future training |
| Food semantic segmentation/classification repos | Food group segmentation | Useful for broader food-group analysis |
| YOLO-style food detectors | Rapid MVP bounding boxes | Easier to operationalize than full segmentation |

Architecture rule:

```text
photo → vision proposal (hosted or OSS) → our validation/cleaning
      → item guesses + boxes/masks/confidence
      → food resolution service across multiple sources
      → ranked nutrition candidates
      → user confirms/edits food match + portion
      → confirmed nutrition writes
      → food_entries + health_metrics event group
      → graph edges/history (“last time you ate this…”)
```

Avoid relying on Food-101 style single-label classifiers as the main ingestion layer. They are useful for demos but weak for multi-item T1D meal review.

**Food resolution layer:**

The vision model should only propose candidate food regions and coarse labels. It should not define final nutrition truth.

For each detected label, e.g. `artisan burger` or `sweet potato fries`, the backend should resolve it against multiple food sources:

1. Normalize the label:
   - lowercase
   - singular/plural cleanup
   - spelling cleanup
   - remove noisy adjectives where helpful
2. Search across sources:
   - user-confirmed prior foods
   - curated/Sparky internal database
   - trusted standardized nutrition databases
   - OpenFoodFacts / open community food datasets
   - user-submitted/custom foods
3. Rank candidates by:
   - text similarity
   - source trust
   - country/brand relevance
   - prior user selections
   - meal context
   - macro plausibility
4. Return top matches for confirmation.
5. Only after confirmation, create the canonical meal event.

Source trust hierarchy:

| Priority | Source |
|---|---|
| 1 | User-confirmed prior foods |
| 2 | Curated/Sparky internal DB |
| 3 | High-quality standardized food DBs |
| 4 | Open community food DBs |
| 5 | Model-estimated fallback only if no reliable match exists |

Candidate response shape:

```json
{
  "detected_label": "sweet potato fries",
  "matches": [
    {
      "source": "sparky",
      "food_id": "sp_123",
      "name": "Sweet Potato Fries",
      "carbs_per_100g": 24,
      "score": 0.92
    },
    {
      "source": "openfoodfacts",
      "food_id": "off_456",
      "name": "Sweet potato fries oven baked",
      "carbs_per_100g": 21,
      "score": 0.81
    }
  ]
}
```

Recommended canonical model direction:

- `food_source_records` — raw provider records from Sparky / OFF / USDA / user DB
- `canonical_foods` — normalized food entities controlled by us
- `food_aliases` — alternate names and source mappings
- `meal_item_candidates` — proposed matches before confirmation
- `meal_items` — confirmed chosen items for an actual meal event

This makes the food resolver, provenance, confidence, and user confirmation loop part of the core product IP.

**Collected fields:**

- meal time
- food names
- quantity/portion
- carbs/protein/fat/fiber/calories
- glycemic index/load if known
- meal type
- photo/barcode/provider IDs

**Writes:**

- `food_entries`
- `foods`
- `ContextEvent` meal where needed
- `health_metrics` as `CARBS`, `PROTEIN`, `FAT`, `FIBER`, `CALORIES`, `GLYCEMIC_INDEX`, `GLYCEMIC_LOAD`

**Graph edges to create:**

- `same_event_as` between confirmed macros from the same meal event group
- `meal_to_glucose_spike`
- `meal_to_delayed_spike`
- `correlates_with` recurring meal/food patterns

**Photo-specific graph/provenance fields:**

- visual model name/version
- detected item labels
- bounding boxes or segmentation mask references
- per-item visual confidence
- user-confirmed label/portion override
- nutrition mapping provider and confidence
- final confirmed event group ID

**Primary product questions:**

- “What happened last time I ate this?”
- “Does this kind of meal rise later for me?”
- “Which meals are worth watching?”

---

### Insulin

**Sources:**

- Manual logging
- Future: pump integration
- Future: Apple Health medication/insulin if available

**Collected fields:**

- insulin type
- units
- timestamp
- injection site
- basal/bolus/correction classification
- meal association if provided

**Writes:**

- `ContextEvent` / insulin event fields
- `health_metrics` as `INSULIN`, `INSULIN_BOLUS`, `INSULIN_BASAL`, `INSULIN_CORRECTION`

**Graph edges to create:**

- `insulin_to_glucose_change`
- `same_event_as` linking bolus to meal if logged together
- `precedes` insulin before glucose change

**Safety rule:**

The graph may describe historical insulin timing/outcomes but must not recommend insulin doses.

---

## 4.2 Lifestyle and Wearable Data

### Exercise / Activity

**Sources:**

- Manual exercise logs
- Garmin webhook
- Fitbit/Polar/Strava/Withings future integrations
- Apple Health / HealthKit future

**Collected fields:**

- exercise type
- start/end time
- duration
- intensity
- calories
- distance
- steps
- heart rate during exercise

**Writes:**

- `exercise_entries`
- `activity_entries`
- `health_metrics`: `EXERCISE_MINUTES`, `EXERCISE_CALORIES`, `STEPS`, `DISTANCE_KM`, `FLOORS_CLIMBED`, `HEART_RATE`

**Graph edges:**

- `exercise_to_glucose_drop`
- `exercise_to_glucose_rise`
- `precedes`
- recurring exercise-time correlations

**Questions:**

- “Do I go low after football?”
- “Does walking after lunch help?”
- “How long after exercise do I tend to drop?”

---

### Sleep

**Sources:**

- Manual sleep
- Garmin/Fitbit/Apple Health future

**Collected fields:**

- start/end
- duration
- sleep stages
- sleep score
- awake minutes
- sleep stress/body battery if available

**Writes:**

- `sleep_entries`
- `sleep_stages`
- `health_metrics`: `SLEEP_HOURS`, `SLEEP_DEEP`, `SLEEP_REM`, `SLEEP_LIGHT`, `SLEEP_AWAKE`, `SLEEP_SCORE`, `AVG_SLEEP_STRESS`

**Graph edges:**

- `sleep_to_next_day_glucose`
- `heart_rate_to_low_glucose`
- overnight low relationships

**Questions:**

- “Do poor sleep nights make next day glucose higher?”
- “Are overnight lows linked to low heart rate?”

---

### Heart / Vitals / Body Battery

**Sources:**

- Garmin
- Fitbit
- Apple Health
- Manual vitals

**Collected fields:**

- heart rate
- resting heart rate
- HRV
- SpO2
- respiratory rate
- blood pressure
- body battery/stress

**Writes:**

- respective domain tables
- `health_metrics`: `HEART_RATE`, `RESTING_HEART_RATE`, `HEART_RATE_VARIABILITY`, `SPO2`, `RESPIRATORY_RATE`, `BLOOD_PRESSURE_*`, `BODY_BATTERY_CHANGE`, `STRESS_LEVEL`

**Graph edges:**

- `heart_rate_to_low_glucose`
- `stress_to_glucose_rise`
- `correlates_with`

---

### Mood / Stress / Notes / Memory

**Sources:**

- Manual mood log
- Voice notes
- Chat/user memory
- Future wearable stress metrics

**Collected fields:**

- mood score
- stress level
- energy level
- free text note
- voice transcript
- tags

**Writes:**

- `mood_entries`
- `lifestyle_entries`
- future `memory_notes`
- `health_metrics`: `MOOD_SCORE`, `STRESS_LEVEL`, `ENERGY_LEVEL`, `CUSTOM`

**Graph edges:**

- `stress_to_glucose_rise`
- `correlates_with`
- `precedes`

---

## 5. End-to-End Data Flow

```text
1. Data arrives
   - API form
   - provider webhook
   - OAuth pull sync
   - manual entry
   - photo/barcode
   - voice note

2. Raw payload preserved where useful
   - raw_data / metadata JSON
   - provider_id for dedup

3. Domain table write
   - validation
   - CRUD detail
   - UI source of truth

4. Metric normalization
   - convert to HealthMetricCreate
   - units standardized
   - timestamps normalized
   - source/provider_id captured

5. health_metrics write
   - node created
   - dedup by source/provider_id where possible

6. Graph builder / pattern service
   - search temporal windows
   - detect relationships
   - create health_metric_edges
   - attach evidence + confidence

7. Aggregation/features
   - daily aggregates
   - rolling windows
   - pattern summaries
   - relationship strength summaries

8. AI/RAG context
   - recent glucose/events
   - pattern summaries
   - strongest graph edges
   - relevant subgraph

9. Frontend surfaces
   - Patterns
   - Meal Review
   - Coach
   - Memory
   - Discuss
```

---

## 6. Graph Edge Creation Strategy

There are three ways to create edges.

### 6.1 Synchronous during pattern analysis

Used now for post-meal spikes.

Pros:

- simple
- immediate evidence
- easy tests

Cons:

- only happens when analysis runs
- read endpoints can mutate state if not controlled

Use for MVP.

---

### 6.2 Background graph builder

A scheduled job scans recent data and builds edges.

Pros:

- clean separation
- can backfill history
- avoids side effects in read APIs

Cons:

- needs worker/scheduler
- more moving pieces

Use after initial MVP graph is stable.

---

### 6.3 Ingestion-time linking

When a meal or wearable event arrives, immediately link same-event metrics.

Example:

```text
meal event creates CARBS, FAT, PROTEIN, CALORIES metrics
create same_event_as edges between those metrics
```

Pros:

- excellent graph structure
- helps later pattern matching

Cons:

- needs event/group ID design

Use soon, but after core relationship edges.

---

## 7. ML / AI Pattern Plan

Use staged intelligence. Do not jump straight to black-box ML.

## Stage 1 — Rule-based / statistical evidence

This is safest and explainable.

### Patterns to surface now

#### 1. Post-meal spike

**Why:** High-value T1D pattern, easy to explain.

**How:**

- meal/carbs metric at time T
- glucose baseline before T
- glucose peak within 1–3 hours
- if rise > threshold and peak > target, create edge

**Edge:** `meal_to_glucose_spike`

**Frontend copy:**

> “Last time you logged a meal like this, you went high about 2 hours later.”

---

#### 2. Delayed high-fat spike

**Why:** Common and educational; pizza/high-fat meals are meaningful.

**How:**

- fat/calorie metric at T
- glucose peak 4–7 hours later
- compare to early post-meal period

**Edge:** `meal_to_delayed_spike`

**Copy:**

> “This kind of meal tends to rise later for you.”

---

#### 3. Exercise-related drop/rise

**Why:** Actionable for planning without dosing.

**How:**

- exercise metric at T
- compare glucose baseline before exercise to min/avg 0–12 hours after
- classify drop/rise/stable

**Edges:**

- `exercise_to_glucose_drop`
- `exercise_to_glucose_rise`

**Copy:**

> “You’ve been more active after lunch and lower on average afterwards.”

---

#### 4. Overnight low pattern

**Why:** Safety-relevant.

**How:**

- glucose <70 during sleep window
- link prior exercise, insulin, sleep, heart rate if available

**Edges:**

- `heart_rate_to_low_glucose`
- `sleep_to_next_day_glucose`
- `precedes`

**Copy:**

> “You are waking up around 5 mmol/L most mornings.”

---

#### 5. Time-of-day high/low

**Why:** Useful coaching pattern.

**How:**

- bucket glucose by hour
- repeated highs/lows across days
- link recurring time windows to preceding events

**Edges:**

- `correlates_with`
- `precedes`

**Copy:**

> “You are going high around 6pm most days.”

---

#### 6. Sleep / stress / next-day glucose

**Why:** Differentiates the app beyond diabetes-only logs.

**How:**

- poor sleep score / short sleep / high stress
- next-day average glucose, variability, TIR

**Edge:** `sleep_to_next_day_glucose`, `stress_to_glucose_rise`

**Copy:**

> “After shorter sleep, your mornings have looked less steady.”

---

## Stage 2 — Feature store / rolling aggregates

Once rule edges are stable, compute features:

### Daily features

- avg glucose
- TIR
- time below/above
- coefficient of variation
- total carbs
- total insulin
- exercise minutes
- sleep hours
- sleep score
- average HRV
- stress score
- hydration
- mood

### Event features

For each meal:

- carbs/fat/protein/fiber/calories
- starting glucose
- insulin nearby
- exercise nearby
- sleep quality previous night
- peak glucose 1–3h
- peak glucose 4–7h
- time to peak
- return-to-range time

### Graph features

- edge count by type
- recurring relationship frequency
- average confidence per relationship
- time delay distribution
- strongest source nodes for each adverse glucose node

**Storage options:**

- extend `health_daily_aggregates`
- add `health_feature_windows`
- add materialized views later

---

## Stage 3 — Lightweight ML models

Only after enough personal data exists.

### Candidate models

#### Meal outcome predictor

Predict:

- peak glucose range
- time to peak
- delayed spike risk

Inputs:

- meal macros
- current glucose
- recent trend
- insulin nearby (as historical input only)
- exercise previous 12h
- sleep previous night
- historical edge patterns

Model types:

- gradient boosted trees
- random forest
- calibrated logistic regression

Output copy:

> “Based on similar meals, this may be worth watching later.”

Not allowed:

> “Take X units.”

---

#### Low-risk classifier

Predict:

- risk of low in next 2–6 hours

Inputs:

- current glucose/trend
- exercise recent
- insulin recent
- sleep/HRV/body battery
- past low edges

Use carefully because this approaches medical-device territory. Keep as “worth watching” pattern, not alerting/treatment instruction.

---

#### Pattern clustering

Cluster days/meals into types:

- steady day
- late-spike day
- exercise-drop day
- poor-sleep-high day
- overnight-low day

Useful for Coach/Memory.

---

## Stage 4 — LLM / AI reasoning over graph

LLM should not infer from raw noise alone. It should receive compact, precomputed graph evidence.

RAG context should include:

```text
recent readings
recent events
pattern summaries
strongest graph edges
relevant subgraph for the user question
safety rules
```

Example graph context:

```text
meal_to_glucose_spike: CARBS 80g → BLOOD_GLUCOSE 230mg/dL
confidence 0.82, delay 120 min
evidence: pizza, baseline 110, rise +120
```

AI output:

> “Educationally, meals like this have sometimes been followed by a rise for you around 2 hours later. It may be worth reviewing what happened last time and discussing recurring patterns with your care team.”

---

## 8. Product Surfaces: What We Show and Why

### Home

Shows:

- today’s glucose status
- top 3 observations
- one main action

Graph usage:

- strongest recent edges
- new/worsening recurring patterns

Example:

> “Today looks steadier than yesterday.”

---

### Hoot & Holla

Shows:

- chat
- mic/text/photo/barcode
- prompt chips

Graph usage:

- question-specific subgraph retrieval
- relationship evidence in RAG

Example prompts:

- “Why am I high right now?”
- “What happened last time?”
- “Why have I been low after lunch?”

---

### Meal Review

Shows:

- AI-recognized foods
- user correction
- similar meal history
- graph-backed evidence

Graph usage:

- meal → glucose edges
- high-fat delayed edges
- same-food/same-macro clusters

Example:

> “Last time you logged a meal like this, you went high about 3 hours later.”

---

### Patterns

Shows:

- card-led pattern system
- light grading: Good / Worth watching / Needs attention

Graph usage:

- recurring edges grouped into user-readable cards

Example:

> “You had a low and your heart rate was unusually low at the same time.”

---

### Pattern Detail

Shows:

- why noticed
- when started
- what may matter
- evidence
- actions

Graph usage:

- subgraph around the pattern
- source nodes and target nodes

Actions:

- Save as note
- Add voice note
- Talk to mummy
- Bring to doctor
- Compare with last time

---

### Coach

Shows:

- progress and gentle gamification
- recurring improvements

Graph usage:

- positive edges / improving relationships
- reduced spike frequency
- improved TIR clusters

Example:

> “10 days of steadier mornings.”

---

### Memory

Shows:

- saved graph observations
- voice notes
- clinic notes
- important events

Graph usage:

- saved pattern cards become memory records
- memory notes can be linked back to graph edges

---

## 9. Data Quality and Governance

### Timestamp normalization

Critical because graph edges depend on timing.

Rules:

- Store canonical timestamps in UTC.
- Preserve source timezone in metadata when useful.
- Normalize SQLite test comparisons where needed.
- All edge `time_delay_seconds` uses normalized UTC.

### Unit normalization

Rules:

- Blood glucose canonical: mg/dL internally, display user preference.
- Weight canonical: kg.
- Distance canonical: km.
- Sleep canonical: hours.
- Exercise canonical: minutes.
- Water canonical: ml or liters — pick one and document.

### Deduplication

Use:

- `provider_id` when source provides stable IDs
- `(user_id, type, source, provider_id)` for metrics
- `(source_metric_id, target_metric_id, edge_type)` for edges

### Provenance

Every metric and edge should know:

- source
- provider ID
- algorithm
- evidence
- created timestamp

### Privacy

Health graph is highly sensitive.

Requirements:

- user scoping on all queries
- no cross-user edges
- no provider secrets in metadata
- future export/delete support

---

## 10. Immediate Engineering Actions

## A. Complete graph edge persistence

### A1. Exercise edges

- Detect exercise impact.
- Find nearest `EXERCISE_MINUTES` metric and target glucose metric.
- Create:
  - `exercise_to_glucose_drop`
  - `exercise_to_glucose_rise`
- Evidence:
  - duration
  - intensity
  - baseline
  - min/avg after
  - drop/rise
  - hours monitored

### A2. Delayed high-fat meal edges

- Extend delayed high-fat detection.
- Find nearest `FAT` / `CALORIES` metric and delayed glucose peak.
- Create `meal_to_delayed_spike`.

### A3. Overnight low relationship edges

- Link sleep/heart/vitals metrics to overnight low glucose.
- Start simple:
  - if low occurs overnight and heart rate metric exists nearby, create `heart_rate_to_low_glucose`
  - if sleep metric exists for same night, create `sleep_to_next_day_glucose` or generic `correlates_with`

### A4. Insulin edges

- Link insulin metrics to subsequent glucose change.
- Keep language strictly historical.
- Evidence:
  - insulin type
  - time to glucose change
  - direction/magnitude

---

## B. Add graph backfill job

Create a script/service:

```text
scripts/backfill_graph_edges.py
```

Steps:

1. For each user
2. For each date window
3. Run pattern detectors with `persist_graph_edges=True`
4. Upsert edges
5. Report counts by edge type

Acceptance:

- Can rebuild graph edges from existing metrics/events.

---

## C. Add graph feature summaries

Add service methods:

- strongest recurring relationships
- edge count by type
- edge confidence trend over time
- top causes for highs/lows
- top protective relationships

Potential table later:

```text
health_graph_summaries
```

---

## D. Improve RAG retrieval

Current RAG includes top strongest edges globally.

Needed:

- classify user query intent
- retrieve relevant edge types
- retrieve subgraph around recent/current metric
- keep prompt compact

Examples:

| Query | Graph retrieval |
|---|---|
| “Why am I high?” | incoming edges to recent high glucose metric |
| “What happened last time I ate pizza?” | meal/food edges with matching evidence food_name |
| “Why low after lunch?” | exercise/insulin/meal edges before low glucose in lunch window |
| “What should I bring to doctor?” | highest-confidence recurring edges + safety-relevant lows |

---

## E. Frontend graph surfaces

MVP graph UI:

1. Pattern Detail evidence list
2. Meal Review “last time / similar meals”
3. Memory saved graph notes
4. Coach progress cards

Do not build complex node-link graph visualization yet. It is likely less useful than explainable cards.

---

## 11. Suggested Implementation Sequence

```text
1. Exercise graph edges + tests
2. Delayed high-fat graph edges + tests
3. Overnight/sleep/heart graph edges + tests
4. Insulin historical graph edges + tests
5. Graph backfill script
6. Better RAG graph retrieval
7. Pattern Detail / Meal Review graph UI
8. Graph summary service
9. Documentation refresh
10. Safety review
```

---

## 12. Acceptance Criteria for the Data Graph MVP

- [ ] Every core domain writes normalized `health_metrics`.
- [ ] Pattern detectors persist edges for at least:
  - meal → spike
  - high-fat meal → delayed spike
  - exercise → glucose drop/rise
  - sleep/heart → overnight low
- [ ] Graph API can return:
  - edges
  - neighbors
  - causes
  - effects
  - subgraph
  - recent correlations
- [ ] RAG includes graph evidence.
- [ ] Chat can answer “what happened last time?” using graph evidence.
- [ ] Frontend Pattern Detail can show evidence behind a pattern.
- [ ] Tests cover graph creation, dedup, user scoping, RAG context, and safety.
- [ ] Full test suite passes.

---

## 13. Risks and Mitigations

### Risk: Graph becomes pseudo-causal too early

**Problem:** Users may interpret correlations as medical certainty.

**Mitigation:** Use language: “may”, “has been followed by”, “worth reviewing”, “observational evidence”. Avoid “caused”.

---

### Risk: Prompt bloat

**Problem:** Feeding too many edges into the LLM wastes context and confuses output.

**Mitigation:** Retrieve query-specific subgraphs. Limit to top 5–10 edges. Summarize compactly.

---

### Risk: Edge spam

**Problem:** Every analysis run creates duplicate/noisy edges.

**Mitigation:** Use upsert dedup. Add confidence thresholds. Add backfill jobs with dry-run reporting.

---

### Risk: Data sparsity

**Problem:** Many users may not have enough logged meals/exercise/sleep.

**Mitigation:** Surface “not enough data yet” states. Use onboarding to encourage logging. Do not overclaim.

---

### Risk: Medical-device boundary

**Problem:** Low prediction/insulin relationships may look like treatment advice.

**Mitigation:** Keep product framed as educational companion. No real-time alerts or dosing recommendations without clinical/regulatory path.

---

### Risk: Provider data inconsistency

**Problem:** Garmin/Fitbit/Apple Health use different units and schemas.

**Mitigation:** Central provider parsers normalize into `HealthMetricCreate`. Preserve raw data in metadata.

---

## 14. Big Picture: What This Enables

Once complete, the app can become a trusted diabetes memory system:

```text
It remembers what happened.
It links related events.
It explains patterns with evidence.
It helps users prepare better questions.
It supports conversations with parents/clinicians.
It stays away from medical advice and dosing.
```

That is the product differentiator.

The graph is not just storage. It is the foundation for:

- meal memory
- pattern cards
- safe coaching
- clinic-ready summaries
- personalized RAG
- future ML features
- explainable AI
