# T1D Companion — Master TODO

**Last synced:** 2026-05-18
**Sources:** GRAPH_TODO.md, SPRINT_PLAN.md, progress.md, phase plans

---

## Legend

- `[ ]` = not started
- `[x]` = done
- `[~]` = in progress
- Blocked items noted with `⛔`

---

## Sprint 1: Safety Lockdown

- [x] **S1-01:** Post-LLM safety validation — block dosing/treatment advice
- [x] **S1-02:** Deduplicate SafetyAgent → delegate to SafetyScaffold
- [x] **S1-03:** Safety-focused chat tests (dosing blocked, emergency short-circuit, safe passes)

## Sprint 2: Frontend Screen Consolidation

- [ ] **S2-01:** Merge chat screens → Hoot & Holla (mic, camera, barcode, prompt chips)
- [ ] **S2-02:** Merge meal screens → Meal Review flow (4-step: capture → analysing → review → memory)
- [ ] **S2-03:** Merge pattern screens → Patterns (card-led, light grading, plain English)
- [ ] **S2-04:** Add Coach page (progress streaks, gentle achievements)
- [ ] **S2-05:** Add Memory page (saved observations, voice notes, clinic notes)
- [ ] **S2-06:** Add Discuss page (share with caregivers/clinicians)
- [ ] **S2-07:** Update navigation + routing (clean nav: Home, Hoot & Holla, Meal Review, Patterns, Coach, Memory, Discuss)
- [ ] **S2-08:** Copy pass — plain English everywhere (no marketing fluff)

## Sprint 3: Security + Deployment Hardening

- [ ] **S3-01:** Add rate limiting (login 5/min, register 3/min, chat 30/min)
- [ ] **S3-02:** Remove hardcoded demo login → env-var gated (`VITE_ENABLE_DEMO=true`)
- [ ] **S3-03:** Dual-write verification tests (domain creates → health_metrics)
- [ ] **S3-04:** API smoke test script (all 25 endpoints respond)
- [ ] **S3-05:** Demo data seeder (realistic multi-day data across 16 domains)
- [ ] **S3-06:** Production Docker compose (PostgreSQL + backend + frontend + Alembic)

## Sprint 4: Code Quality + Provider Showcase

- [ ] **S4-01:** Service method naming consistency (`create`/`list`/`get`/`delete` across all domains)
- [ ] **S4-02:** Add missing `__init__.py` files for all domain packages
- [ ] **S4-03:** Garmin webhook end-to-end
- [ ] **S4-04:** Connected devices UI (provider status, "coming soon" labels)
- [ ] **S4-05:** Warning cleanup (Pydantic V2, SQLAlchemy deprecations, datetime.utcnow)

## Sprint 5: CI/CD + Launch Prep

- [ ] **S5-01:** GitHub Actions CI pipeline (pytest + tsc + alembic check)
- [ ] **S5-02:** Health endpoint metrics (`/health` with service statuses)
- [ ] **S5-03:** Database backup script (`pg_dump`)
- [ ] **S5-04:** Production deployment docs

---

## Graph — Event Grouping

- [ ] Add `event_group_id` column to `health_metrics` + index `(user_id, event_group_id)`
- [ ] Update `HealthMetricCreate` / `HealthMetricResponse` schemas
- [ ] Update `HealthMetricService.create()` and `create_batch()`
- [ ] Meals: assign one `event_group_id` to CARBS/FAT/PROTEIN/FIBER/CALORIES from same meal
- [ ] Photo-confirmed meals: preserve visual detection provenance in metadata
- [ ] Exercise: assign one `event_group_id` to workout-derived metrics
- [ ] Insulin: assign one `event_group_id` to related insulin metrics
- [ ] Sleep: assign one `event_group_id` to nightly sleep metrics
- [ ] Garmin/Fitbit ingestion: preserve provider event/session IDs in `event_group_id`
- [ ] Create `same_event_as` edges between metrics sharing `event_group_id`
- [ ] Add graph service helper: `link_event_group(user_id, event_group_id)`
- [ ] Tests: event grouping + same-event edge dedup

## Graph — Schema Migrations

- [x] Alembic migration for `health_metric_edges`
- [x] Indexes: `(user_id, source_metric_id)`, `(user_id, target_metric_id)`, `(user_id, edge_type)`, `(user_id, edge_type, confidence)`, unique `(source_metric_id, target_metric_id, edge_type)`
- [x] Foreign keys to `health_metrics.id` with cascade
- [x] Check constraint: `0 <= confidence <= 1`
- [ ] Add `event_group_id` to `health_metrics`
- [ ] Add `provenance_json` to `health_metric_edges`
- [ ] Add `confidence_components_json` to `health_metric_edges`
- [ ] Add `window_start` / `window_end` to `health_metric_edges`
- [ ] Verify SQLite test compatibility + Postgres target

## Graph — Service Layer

- [x] `create_edge()`
- [x] `upsert_edge()` / dedup logic
- [ ] `get_edges_for_metric()`
- [x] `get_neighbors()`
- [x] `get_causes(metric_id)`
- [x] `get_effects(metric_id)`
- [ ] `get_recent_correlations(user_id, days=14)`
- [x] `get_subgraph(user_id, center_metric_id, depth=1)`
- [x] `get_strongest_edges(user_id, edge_types=None, limit=20)`
- [ ] `get_event_group(user_id, event_group_id)`
- [ ] `link_event_group(user_id, event_group_id)`
- [ ] Aggregation helpers: edge count by type, avg confidence by type, strongest recurring pairs

## Graph — Pattern Detections → Edges

- [x] Post-meal spike: meal/carbs → glucose spike (`meal_to_glucose_spike`)
- [ ] Delayed high-fat: fat/calories → delayed spike (`meal_to_delayed_spike`)
- [ ] Exercise impact: exercise → glucose drop/rise (`exercise_to_glucose_drop` / `exercise_to_glucose_rise`)
- [ ] Overnight low: sleep/heart → low glucose (`heart_rate_to_low_glucose`, `sleep_to_next_day_glucose`)
- [ ] Insulin historical: insulin → subsequent glucose change (`insulin_to_glucose_change`)
- [ ] Correlation analysis: persist aggregate relationship edges
- [ ] Make edge-writing optional/configurable to avoid duplicate writes

## Graph — Provenance

- [ ] Ensure every normalized metric preserves `source`, `provider_id`, raw metadata
- [ ] Add/version `metadata` conventions where inconsistent
- [ ] Add `provenance_json` to `health_metric_edges`
- [ ] Store: detector name, version, run type, run ID, feature window, code commit
- [ ] Add helper builders for consistent edge provenance payloads
- [ ] Add detector version constants
- [ ] Tests: provenance presence and structure

## Graph — Confidence Decomposition

- [ ] Add `confidence_components_json` to `health_metric_edges`
- [ ] Components: repetition, temporal_consistency, effect_size, data_completeness, source_quality, recency
- [ ] Create shared scoring utility for graph detectors
- [ ] Compute `confidence_overall` from weighted component scores
- [ ] UI/RAG wording thresholds: low="sometimes", medium="has sometimes been followed by", high="has often been followed by"
- [ ] Tests: confidence calculation + thresholded language mapping

## Graph — API Endpoints

- [x] `POST /api/v1/metrics/graph/edges`
- [x] `GET /api/v1/metrics/graph/edges` (query by type, confidence, source/target)
- [x] `GET /api/v1/metrics/graph/metrics/{metric_id}/neighbors`
- [x] `GET /api/v1/metrics/graph/metrics/{metric_id}/causes`
- [x] `GET /api/v1/metrics/graph/metrics/{metric_id}/effects`
- [x] `GET /api/v1/metrics/graph/subgraph`
- [x] `GET /api/v1/metrics/graph/recent-correlations`
- [x] Wire router in `app/main.py`
- [ ] Add event-group query endpoint
- [ ] Replace placeholder `user_id` with dependency-injected auth

## Graph — RAG Integration

- [x] Extend `RAGContext` with `graph_edges`
- [x] Update `LLMService.retrieve_context()` to query graph service
- [x] Update `DataIngestionAgent` context output
- [x] Update system prompt formatting (relationship triples)
- [ ] Ensure safety wording remains observational
- [ ] Retrieve only query-relevant edge types
- [ ] Cap retrieved edges to top 5–10 by relevance/confidence
- [ ] Suppress weak/ambiguous edges from LLM context
- [ ] Tests: RAG evidence contract

## Graph — Tests

- [x] Model/schema import tests
- [x] Migration/table creation tests
- [x] `create_edge()` test
- [x] Edge dedup/upsert test
- [x] Neighbor query test
- [x] Cause/effect query test
- [x] Subgraph query test
- [x] PatternService creates meal→spike edge test
- [ ] PatternService creates exercise→drop edge test
- [x] Graph API auth/user-scoping test
- [x] Graph RAG context test
- [ ] Safety test: graph-derived response must not produce dosing advice
- [ ] Event grouping tests
- [ ] Same-event edge dedup tests
- [ ] Provenance structure tests
- [ ] Confidence component/scoring tests
- [ ] RAG evidence contract tests

## Photo Meal Ingest

- [ ] Evaluate FoodSAM for food segmentation
- [ ] Evaluate YOLO-style food detector for bounding-box MVP
- [ ] Add swappable interface: `analyze_meal_image(image) -> MealImageAnalysisProposal`
- [ ] Hosted vision model implementation for v1
- [ ] Strict JSON response contract for hosted vision prompts
- [ ] Validate and clamp proposals (max items, confidence thresholds, bbox bounds)
- [ ] Store raw model output as provisional metadata only

## Food Resolution Layer

- [ ] Add `FoodResolutionService` after vision proposal, before user confirmation
- [ ] Normalize detected labels (lowercase, plural cleanup, spelling, remove adjectives)
- [ ] Search sources in priority: user-confirmed → curated/Sparky DB → standardized DBs → open community → model fallback
- [ ] Rank candidates by: text similarity, source trust, country/brand relevance, prior user selections, meal context, macro plausibility
- [ ] Return top matches per detected item
- [ ] Design canonical model: `food_source_records`, `canonical_foods`, `food_aliases`, `meal_item_candidates`, `meal_items`
- [ ] Decide: extend existing `foods`/`food_entries` or create new tables

## Photo + Food Provenance

- [ ] Include visual inference provider (`hosted`/`self_hosted`) in provenance
- [ ] Include visual model name/version in metric provenance
- [ ] Include prompt/template version for hosted models
- [ ] Include validation decisions: dropped items, clamped confidences, user edits
- [ ] Include user override flags in metadata/provenance
- [ ] Include nutrition mapping provider/confidence
- [ ] Include food resolver score and source trust rank
- [ ] Ensure RAG copy says "estimated" and "reviewed" appropriately

## Documentation

- [ ] Update `CONTEXT.md` — define Health Metric node, Edge, Evidence, Confidence, Time Delay
- [ ] Update `ARCHITECTURE_MAP.md` — add graph data flow
- [ ] Update `CODEBASE_AUDIT.md` — reflect implemented graph architecture
- [x] `GRAPH_ARCHITECTURE.md` — schema, edge types, query examples, RAG context
- [x] `DATA_DESIGN_FLOW_PLAN.md` — data collection, graph flow, ML/AI roadmap
- [ ] Link to PHL/PHKG research reference

## Review + Harden

- [x] Run full test suite (304+ passing)
- [ ] Run frontend build if graph UI touched
- [ ] Check Alembic migration chain
- [ ] Check for circular imports
- [ ] Check API user scoping and auth
- [ ] Check graph-derived copy for safety risks
- [ ] Produce final implementation summary
