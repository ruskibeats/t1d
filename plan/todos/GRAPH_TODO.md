# T1D Companion — Central Data Graph TODO

**Purpose:** Build the central data graph feed database: a persistent graph layer where every health metric is a node and correlations/patterns are stored as edges.

> Graph edges are observational evidence, not treatment advice.  
> New graph work must preserve provenance, explain confidence, and support safe non-prescriptive RAG output.

**Current foundation:**
- `health_metrics` already exists as the unified node table.
- Domain services already dual-write into `health_metrics`.
- `health_metric_edges` now exists as the relationship table.
- `HealthGraphService` and `/api/v1/metrics/graph/...` endpoints exist.
- Pattern detection currently persists `meal_to_glucose_spike` edges.
- RAG now includes compact graph relationship evidence.

---

## 0. Event grouping foundation

### 0.1 Add `event_group_id` to `health_metrics`

- [ ] Add nullable UUID/string `event_group_id` column to `health_metrics`.
- [ ] Add index `(user_id, event_group_id)`.
- [ ] Backfill existing rows as null.
- [ ] Update `HealthMetricCreate` and `HealthMetricResponse`.
- [ ] Update `HealthMetricService.create()` and `create_batch()`.

### 0.2 Group multi-metric ingestion events

- [ ] Meals: assign one `event_group_id` to `CARBS` / `FAT` / `PROTEIN` / `FIBER` / `CALORIES` metrics created from the same meal.
- [ ] Photo-confirmed meals: preserve visual detection provenance and user-confirmed item overrides in meal metric metadata.
- [ ] Exercise: assign one `event_group_id` to workout-derived metrics.
- [ ] Insulin: assign one `event_group_id` to related insulin metrics from the same log/import.
- [ ] Sleep: assign one `event_group_id` to nightly sleep metrics for the same session.
- [ ] Garmin/Fitbit/etc. provider ingestion: preserve provider event/session IDs in `event_group_id` when stable.

### 0.3 Add same-event graph linking

- [ ] Optionally create `same_event_as` edges between metrics sharing `event_group_id`.
- [ ] Keep dedup strict: one edge per `(source_metric_id, target_metric_id, edge_type)`.
- [ ] Add graph service helper: `link_event_group(user_id, event_group_id)`.
- [ ] Add tests for same-event edge dedup.

**Acceptance:**
- New grouped ingestions create a stable `event_group_id`.
- Meal/exercise/sleep/insulin metrics can be queried as one event cluster.
- Tests cover event grouping and same-event edge dedup.

---

## 1. Design graph schema

- [x] Define graph vocabulary:
  - **Node:** `HealthMetric`
  - **Edge:** relationship between two HealthMetric nodes
  - **Evidence:** metadata explaining why the edge exists
  - **Confidence:** numeric relationship strength
  - **Time delay:** delay between source metric and target metric
- [x] Decide whether graph edges only link `health_metrics` rows.
  - Decision for MVP: graph edges link `health_metrics` rows only. Domain entities remain provenance/evidence references.
- [x] Define edge types:
  - `meal_to_glucose_spike`
  - `meal_to_delayed_spike`
  - `exercise_to_glucose_drop`
  - `exercise_to_glucose_rise`
  - `insulin_to_glucose_change`
  - `sleep_to_next_day_glucose`
  - `stress_to_glucose_rise`
  - `heart_rate_to_low_glucose`
  - `hydration_to_glucose_stability`
  - `correlates_with`
  - `precedes`
  - `same_event_as`
- [x] Decide confidence scoring rules.
  - Current: simple detector-specific score.
  - Target: decomposed confidence components.
- [x] Decide deduplication strategy.
  - Current: unique `(source_metric_id, target_metric_id, edge_type)`.
- [x] Decide edge creation timing.
  - Current: synchronous inside PatternService for MVP.
  - Future: background graph-builder/backfill jobs.

**Acceptance:** Clear schema decision documented before implementation.

---

## 2. Implement graph models and schemas

- [x] Add SQLAlchemy model: `HealthMetricEdge`.
- [x] Add enum: `GraphEdgeType`.
- [x] Add Pydantic schemas:
  - `HealthMetricEdgeCreate`
  - `HealthMetricEdgeResponse`
  - `HealthMetricEdgeQuery`
  - `HealthSubgraphResponse`
  - `GraphNeighborResponse`
- [x] Implemented fields:
  - `id`
  - `user_id`
  - `source_metric_id`
  - `target_metric_id`
  - `edge_type`
  - `confidence`
  - `time_delay_seconds`
  - `algorithm`
  - `evidence`
  - `created_at`
  - `updated_at`
- [ ] Planned fields from taxonomy extension:
  - `window_start`
  - `window_end`
  - `confidence_components`
  - `provenance`
  - optional `direction`
- [ ] Add relationships to `HealthMetric` if useful.
- [x] Add forward references in `app/db/models.py` so Alembic discovers the model.

**Acceptance:** Model and schemas import cleanly.

---

## 3. Schema migrations

- [x] Create Alembic migration for `health_metric_edges`.
- [x] Add indexes:
  - `(user_id, source_metric_id)`
  - `(user_id, target_metric_id)`
  - `(user_id, edge_type)`
  - `(user_id, edge_type, confidence)`
  - `(source_metric_id, target_metric_id, edge_type)` unique/dedup path
- [x] Add foreign keys to `health_metrics.id` with cascade behavior.
- [x] Add check constraint for confidence range `0 <= confidence <= 1`.
- [ ] Add `event_group_id` to `health_metrics`.
- [ ] Add `provenance_json` to `health_metric_edges`.
- [ ] Add `confidence_components_json` to `health_metric_edges`.
- [ ] Add `window_start` and `window_end` to `health_metric_edges`.
- [ ] Add indexes:
  - `health_metrics(user_id, event_group_id)`
  - `health_metric_edges(user_id, edge_type)`
  - `health_metric_edges(source_metric_id, target_metric_id, edge_type)` unique/dedup path
- [ ] Verify against SQLite test compatibility.
- [ ] Verify against Postgres target if available.

**Acceptance:** `alembic upgrade head` succeeds; tests can create graph tables.

---

## 4. Build graph service layer

Create/use `app/metrics/graph_service.py`.

- [x] Implement `create_edge()`.
- [x] Implement `upsert_edge()` / dedup logic.
- [ ] Implement `get_edges_for_metric()`.
- [x] Implement `get_neighbors()`.
- [x] Implement `get_causes(metric_id)`.
- [x] Implement `get_effects(metric_id)`.
- [ ] Implement `get_recent_correlations(user_id, days=14)`.
- [x] Implement `get_subgraph(user_id, center_metric_id, depth=1)`.
- [x] Implement `get_strongest_edges(user_id, edge_types=None, limit=20)`.
- [ ] Implement `get_event_group(user_id, event_group_id)`.
- [ ] Implement `link_event_group(user_id, event_group_id)`.
- [ ] Implement aggregation helpers:
  - edge count by type
  - average confidence by type
  - strongest recurring relationship pairs

**Acceptance:** Service has tests for create/query/dedup/subgraph/event-group behavior.

---

## 5. Wire pattern detections to graph edges

Update `PatternService` so detected relationships become persistent graph edges.

- [x] Post-meal spike detection:
  - Link meal/carbs metric → glucose spike metric.
  - Edge type: `meal_to_glucose_spike`.
  - Evidence: carbs, pre-meal baseline, peak value, rise, time-to-peak.
- [ ] Delayed high-fat meal detection:
  - Link fat/calories metric → delayed glucose spike metric.
  - Edge type: `meal_to_delayed_spike`.
  - Evidence: fat grams, hours-to-peak, delayed rise.
- [ ] Exercise impact detection:
  - Link exercise metric → low/high/stable glucose metric.
  - Edge type: `exercise_to_glucose_drop` or `exercise_to_glucose_rise`.
  - Evidence: duration, intensity, baseline, min/avg glucose change.
- [ ] Overnight low detection:
  - Link sleep metrics / heart metrics if available → low glucose metric.
  - Edge type: `heart_rate_to_low_glucose`, `sleep_to_next_day_glucose`, or `correlates_with`.
- [ ] Insulin historical relationship detection:
  - Link insulin metric → subsequent glucose change.
  - Edge type: `insulin_to_glucose_change`.
  - Must remain historical/observational only.
- [ ] Correlation analysis:
  - Persist aggregate relationship edges, not only JSON response.
- [ ] Make edge-writing optional/configurable to avoid duplicate writes during read-only analyses.

**Acceptance:** Running pattern detection creates graph edges with evidence metadata.

---

## 5A. Provenance tracking

### 5A.1 Metric provenance normalization

- [ ] Ensure every normalized metric preserves:
  - `source`
  - `provider_id`
  - raw/source metadata needed for audit
- [ ] Add/version `metadata` conventions where inconsistent.
- [ ] Add optional metric provenance JSON if schema extension is accepted.

### 5A.2 Edge provenance schema

- [ ] Add `provenance_json` / `provenance` to `health_metric_edges` if not already present.
- [ ] Store:
  - detector name
  - detector version
  - run type (`realtime` / `backfill`)
  - run ID
  - feature window
  - code commit/version where available

### 5A.3 Provenance helpers

- [ ] Add helper builders for consistent edge provenance payloads.
- [ ] Ensure all graph detectors call shared provenance builder.
- [ ] Add detector version constants.

**Acceptance:**
- Every persisted edge can answer:
  - which detector created it
  - which version created it
  - whether it came from realtime or backfill
  - which window was analyzed
- Tests validate provenance presence and structure.

---

## 5C. Photo meal ingest layer

### 5C.1 Research and choose MVP visual detector

- [ ] Evaluate FoodSAM for food segmentation / overlays.
- [ ] Evaluate YOLO-style food detector for rapid bounding-box MVP.
- [ ] Keep FoodInsSeg as dataset/fine-tuning reference, not first implementation dependency.
- [ ] Avoid single-label Food-101 classifier as the primary ingestion layer.

### 5C.2 Design photo ingest service contract

- [ ] Add swappable service interface: `analyze_meal_image(image) -> MealImageAnalysisProposal`.
- [ ] Support hosted vision model implementation for v1.
- [ ] Leave self-hosted OSS implementation path behind the same interface.
- [ ] Add strict JSON response contract for hosted vision prompts.
- [ ] Validate and clamp proposals:
  - max item count
  - confidence thresholds
  - bbox/polygon bounds
  - allowed field types
  - fallback to manual logging if confidence is too low
- [ ] Candidate item fields:
  - temporary item ID
  - label
  - normalized label
  - confidence
  - bounding box or mask reference
  - portion guess if available
  - model name/version
  - raw model payload reference
- [ ] Store raw model output as provisional metadata, not final nutrition truth.

### 5C.3 Add food resolution layer

- [ ] Add `FoodResolutionService` after vision proposal and before user confirmation.
- [ ] Normalize detected labels:
  - lowercase
  - singular/plural cleanup
  - spelling cleanup
  - remove noisy adjectives where useful
- [ ] Search sources in priority order:
  - user-confirmed prior foods
  - curated/Sparky internal DB
  - standardized nutrition DBs
  - OpenFoodFacts / open datasets
  - user/custom foods
- [ ] Rank candidates by:
  - text similarity
  - source trust
  - country/brand relevance
  - prior user selections
  - meal context
  - macro plausibility
- [ ] Return top matches per detected item for review.
- [ ] Store candidate matches as provisional, not final meal data.

### 5C.4 Design canonical food resolution data model

- [ ] Add/plan `food_source_records` for raw provider records.
- [ ] Add/plan `canonical_foods` for normalized food entities.
- [ ] Add/plan `food_aliases` for names/source mappings.
- [ ] Add/plan `meal_item_candidates` for proposed matches before confirmation.
- [ ] Add/plan `meal_items` for confirmed chosen items in the meal event.
- [ ] Decide whether to extend existing `foods` / `food_entries` first or create new tables.

### 5C.5 Human confirmation before graph write

- [ ] Add confirmed-item schema for edited labels/portions.
- [ ] Map confirmed items to nutrition providers after confirmation.
- [ ] Write confirmed meal to food tables and `health_metrics` with shared `event_group_id`.
- [ ] Create `same_event_as` edges among confirmed macro metrics.

### 5C.6 Photo and food-resolution provenance

- [ ] Include visual inference provider (`hosted` / `self_hosted`) in provenance.
- [ ] Include visual model name/version in metric provenance.
- [ ] Include prompt/template version for hosted models.
- [ ] Include validation decisions: dropped items, clamped confidences, user edits.
- [ ] Include user override flags in metadata/provenance.
- [ ] Include nutrition mapping provider/confidence.
- [ ] Include food resolver score and source trust rank.
- [ ] Ensure RAG copy says "estimated" and "reviewed" appropriately.

**Acceptance:**
- Photo meal flow can produce editable candidate items.
- The vision model is replaceable behind one interface.
- Food labels are resolved through our matching/ranking service, not trusted directly from the vision model.
- All safety/product logic stays in our code.
- Nothing becomes final graph data until user confirms.
- Confirmed photo meals become grouped metrics and graph-ready meal history.

---

## 5B. Confidence decomposition

### 5B.1 Add confidence components

- [ ] Add `confidence_components_json` / `confidence_components` to `health_metric_edges` if not already present.
- [ ] Store at minimum:
  - repetition
  - temporal_consistency
  - effect_size
  - data_completeness
  - source_quality
  - recency

### 5B.2 Confidence scoring utility

- [ ] Create shared scoring utility for graph detectors.
- [ ] Compute `confidence_overall` from weighted component scores.
- [ ] Keep weights configurable per detector if needed later.

### 5B.3 Language thresholds

- [ ] Define UI/RAG wording thresholds:
  - low confidence: “sometimes”
  - medium confidence: “has sometimes been followed by”
  - high confidence: “has often been followed by”
- [ ] Prevent strong wording when repetition or temporal consistency is weak.

**Acceptance:**
- New graph edges persist both overall confidence and component breakdown.
- Confidence is explainable in API and RAG context.
- Tests cover confidence calculation and thresholded language mapping.

---

## 6. Add graph API endpoints

Current implementation is under `/api/v1/metrics/graph`.

- [x] `POST /api/v1/metrics/graph/edges`
- [x] `GET /api/v1/metrics/graph/edges`
  - Query by type, confidence, source/target metric.
- [x] `GET /api/v1/metrics/graph/metrics/{metric_id}/neighbors`
  - Return incoming and outgoing edges.
- [x] `GET /api/v1/metrics/graph/metrics/{metric_id}/causes`
  - Return likely causes of a metric/event.
- [x] `GET /api/v1/metrics/graph/metrics/{metric_id}/effects`
  - Return likely effects following a metric/event.
- [x] `GET /api/v1/metrics/graph/subgraph`
  - Return nodes + edges around a time window or center metric.
- [x] `GET /api/v1/metrics/graph/recent-correlations`
  - Return strongest recent edges for dashboard/RAG.
- [x] Wire router in `app/main.py` via existing metrics router.
- [ ] Add event-group query endpoint after `event_group_id` exists.
- [ ] Replace placeholder `user_id` query pattern with dependency-injected auth for graph endpoints.

**Acceptance:** Authenticated graph endpoints return user-scoped graph data.

---

## 7. Feed graph context into RAG

Update AI context assembly to use the graph layer.

- [x] Extend `RAGContext` with graph fields:
  - `graph_edges`
- [x] Update `LLMService.retrieve_context()` to query graph service.
- [x] Update `DataIngestionAgent` context output to include graph relationships.
- [x] Update system prompt formatting:
  - Include relationship triples like: `meal/carbs → glucose spike, confidence 0.82, delay 150min`.
  - Keep context compact and plain-English.
- [ ] Ensure safety wording remains observational, not prescriptive.

### RAG graph evidence contract

- [ ] Retrieve only query-relevant edge types and neighboring nodes.
- [ ] Include:
  - edge_type
  - confidence_overall
  - confidence_components_json
  - time_delay_seconds
  - compact evidence_json
  - provenance_json (detector/version only, compact)
- [ ] Cap retrieved edges to top 5–10 by relevance/confidence.
- [ ] Suppress weak or ambiguous edges from LLM context unless user asks for raw detail.

**Acceptance:**
- “What happened last time?” queries return event-group and edge-aware evidence.
- RAG explanations cite observational evidence, not raw unsupported guesses.
- Safety layer blocks dosing/treatment-style completions.

---

## 8. Add graph tests

- [x] Model/schema import tests.
- [x] Migration/table creation tests.
- [x] `HealthGraphService.create_edge()` test.
- [x] Edge dedup/upsert test.
- [x] Neighbor query test.
- [x] Cause/effect query test.
- [x] Subgraph query test.
- [x] PatternService creates meal→spike edge test.
- [ ] PatternService creates exercise→drop edge test.
- [x] Graph API auth/user-scoping test.
- [x] Graph RAG context test.
- [ ] Safety test: graph-derived response must not produce dosing advice.
- [ ] Event grouping tests.
- [ ] Same-event edge dedup tests.
- [ ] Provenance structure tests.
- [ ] Confidence component/scoring tests.
- [ ] RAG evidence contract tests.

**Acceptance:** Full test suite passes; graph tests cover critical paths.

---

## 9. Document graph architecture

Update docs:

- [ ] `CONTEXT.md`
  - Define Health Metric node, Health Metric Edge, Evidence, Confidence, Time Delay.
- [ ] `ARCHITECTURE_MAP.md`
  - Add graph data flow.
- [ ] `CODEBASE_AUDIT.md`
  - Update from “missing graph edges” to implemented architecture once complete.
- [x] `GRAPH_ARCHITECTURE.md`
  - Schema, edge types, query examples, RAG context examples.
- [x] `DATA_DESIGN_FLOW_PLAN.md`
  - Data collection, graph flow, ML/AI pattern roadmap.
- [ ] Link to PHL/PHKG research reference.

**Acceptance:** Another agent/developer can understand graph purpose and implementation from docs alone.

---

## 10. Review and harden

- [x] Run `python3 -m pytest tests/ -q` after first graph layer.
  - Latest known: `304 passed`.
- [ ] Run frontend build if graph UI touched.
- [ ] Check Alembic migration chain.
- [ ] Check for circular imports.
- [ ] Check API user scoping and auth.
- [ ] Check graph-derived copy for safety risks.
- [ ] Produce final implementation summary.

**Acceptance:** Tests pass, docs updated, no known blockers.

---

## Suggested implementation order

```text
1. Event grouping foundation (`event_group_id`)
2. Exercise graph edges + tests
3. Delayed high-fat graph edges + tests
4. Overnight/sleep/heart graph edges + tests
5. Insulin historical graph edges + tests
6. Provenance tracking for graph edges
7. Confidence decomposition + scoring utility
8. Photo meal ingest MVP contract
9. Graph backfill script
10. Better RAG graph retrieval
11. Pattern Detail / Meal Review graph UI
12. Graph summary service
13. Documentation refresh
14. Safety review
```

---

## Key Design Questions

1. Should edge creation happen during pattern analysis, during ingestion, or in a separate background graph-builder job for each detector?
2. Should graph edges be immutable evidence records, or should repeated detections update confidence on one aggregate edge?
3. How much graph context should be passed into the LLM without bloating prompts?
4. Should the frontend visualize graph relationships now, or only use them behind the scenes for AI/RAG?
5. Should event grouping use random UUIDs, deterministic provider/session IDs, or both?
