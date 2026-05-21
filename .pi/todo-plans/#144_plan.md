# Clanker Ops #144: [IMPLEMENT] GraphEdgeRuleEngine with 20 rules + temporal proximity

Status: pending
Owner: @clanker
Tags: #implementation #graph #rules
Branch: research/synthea-ingestion

## Intended Outcome

A new `GraphEdgeRuleEngine` service is created in `app/services/graph_edge_engine.py` that generates `HealthMetricEdge` entries from synthetic patient data using two strategies: (1) 20 condition-led clinical rules loaded from `config/graph_edge_rules.yaml`, and (2) a temporal proximity heuristic with 4-hour window and exponential decay (confidence 0.3–0.7). The engine is invoked after the `SyntheticIngestionMapper` finishes seeding a patient and produces graph edges that are clinically meaningful and queryable via `HealthGraphService`.

## Step-by-Step

1. **Read source documentation**: Read `docs/research/SYNTHETIC_DATA_PIPELINE.md` (full document) — specifically the "Graph Edge Rules" section with the 20 condition-led rules table and the "Temporal Proximity Heuristic" parameters.

2. **Read existing graph service**: Read `app/metrics/graph_service.py` to understand `HealthGraphService.upsert_edge()` signature and `HealthMetricEdgeCreate` schema.

3. **Read existing edge model**: Read `app/metrics/models.py` to understand `HealthMetricEdge` columns (source_metric_id, target_metric_id, edge_type, confidence, time_delay_seconds, algorithm, etc.).

4. **Read existing edge types**: Read `app/metrics/types.py` to understand `GraphEdgeType` enum values. Add any missing edge types needed by the 20 rules (e.g., `INSULIN_TO_GLUCOSE_DROP`, `MEAL_TO_GLUCOSE_SPIKE`, `EXERCISE_TO_GLUCOSE_DROP`, etc.).

5. **Create `config/graph_edge_rules.yaml`**: Write the YAML configuration file with all 20 rules. Each rule entry:
   ```yaml
   - rule_id: 1
     name: insulin_to_glucose_drop
     source_pattern:
       event_type: "medication"
       description_contains: "insulin"
     target_pattern:
       metric_type: "BLOOD_GLUCOSE"
       value_direction: "decrease"
     edge_type: "INSULIN_TO_GLUCOSE_DROP"
     confidence: 0.85
     time_delay_minutes: [30, 120]
     clinical_rationale: "Insulin administration causes glucose to decrease within 30-120 minutes"
   ```
   All 20 rules from the pipeline doc must be included.

6. **Create `app/services/graph_edge_engine.py`**: Implement the `GraphEdgeRuleEngine` class:
   - `__init__(self, db: AsyncSession)` — accepts async DB session
   - `load_rules(self, config_path: str)` — loads rules from YAML file
   - `apply_condition_led_rules(self, user_id: int)` — iterates over all `HealthMetric` and `ContextEvent` entries for the user, matches source/target patterns from the 20 rules, creates `HealthMetricEdge` entries via `HealthGraphService.upsert_edge()`
   - `apply_temporal_proximity(self, user_id: int)` — finds all metric pairs within 4-hour window not already connected by condition-led edges, creates edges with exponential decay confidence
   - `generate_edges_for_user(self, user_id: int)` — calls both methods above, returns total edge count
   - `_calculate_exponential_decay_confidence(self, time_delay_minutes: float)` — implements decay function: 0.70 at 0-30min, 0.55 at 30-60min, 0.40 at 60-120min, 0.30 at 120-240min, 0.0 below threshold

7. **Implement pattern matching**: For condition-led rules, implement matching logic that checks:
   - `event_type` and `description_contains` for `ContextEvent` source patterns
   - `metric_type` and `value_direction` (increase/decrease from previous reading) for `HealthMetric` target patterns
   - Time delay within the specified `time_delay_minutes` range

8. **Implement edge deduplication**: Before creating an edge, check if an edge already exists between the same source/target metric pair with the same `edge_type`. Skip if duplicate.

9. **Add logging**: Use `app.core.logging_config.get_logger` to log edge creation, skipped duplicates, and rule match counts per user.

10. **Integrate with mapper**: In `app/services/synthetic_ingestion.py`, after `ingest_synthea_directory` finishes mapping all CSV rows for a user, call `GraphEdgeRuleEngine.generate_edges_for_user(user_id)` to populate the graph.

## Verification

- `config/graph_edge_rules.yaml` exists with exactly 20 rules
- `python -c "import yaml; rules = yaml.safe_load(open('config/graph_edge_rules.yaml')); print(len(rules))"` outputs `20`
- `python -c "from app.services.graph_edge_engine import GraphEdgeRuleEngine; print('OK')"` imports without error
- `pytest tests/test_graph_edge_engine.py` passes (unit tests for rule matching, decay function, deduplication)
- Manual test: seed one synthetic patient, run edge generation, verify `HealthMetricEdge` entries exist via `HealthGraphService.query_edges()`
- Verify exponential decay: edges at 15min have confidence ~0.70, edges at 90min have confidence ~0.40, edges at 200min have confidence ~0.30

## Dependencies

- Task #142 (SyntheticIngestionMapper) — edge engine operates on data created by the mapper
- Task #143 (hybrid metadata storage) — `HealthMetric` and `ContextEvent` entries must exist
- `pyyaml` package for YAML parsing (add to `pyproject.toml` dependencies if not present)

## Audit (EOD Report-Back)

Completed by the agent at task completion. Record:
- **Tokens consumed**: approximate total
- **Files changed**: list of modified/created files
- **Stages completed**: which steps were done
- **Stages deferred**: which steps remain (if any)
- **Unexpected issues**: blockers, wrong assumptions, or bugs encountered
- **Artifacts left behind**: temp files, worktrees, debug output
