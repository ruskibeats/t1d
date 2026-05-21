# Clanker Ops #146: [TEST] Write tests and create 80-patient test fixture

Status: pending
Owner: @clanker
Tags: #testing #synthetic
Branch: research/synthea-ingestion

## Intended Outcome

Comprehensive test coverage for the synthetic data pipeline: updated mapper unit tests, new edge engine unit tests, full pipeline integration tests, and a pytest fixture that pre-loads 80 synthetic patients into the test database. All tests pass and the fixture enables any test file to use synthetic patient data via `db_session` and `synthetic_patient` fixtures.

## Step-by-Step

1. **Read source documentation**: Read `docs/research/SYNTHETIC_DATA_PIPELINE.md` — specifically the "Validation Gate" section (4-phase) to understand what must be tested.

2. **Read existing tests**: Read `tests/test_synthetic_ingestion.py` (current stub tests), `tests/conftest.py` (existing fixtures like `db_session`, `test_user`), and `tests/test_api_graph.py` (graph endpoint test patterns).

3. **Read existing services**: Read `app/services/synthetic_ingestion.py` and `app/services/graph_edge_engine.py` to understand the full API surface to test.

4. **Update `tests/test_synthetic_ingestion.py`**: Expand existing tests and add new ones:
   - `test_map_patient_demographics` — verify age_range classification (child/adolescent/adult/elderly)
   - `test_map_patient_email_format` — verify synthetic email format
   - `test_map_observation_glucose` — verify glucose observation → HealthMetric mapping
   - `test_map_observation_weight` — verify weight observation → HealthMetric + metadata
   - `test_map_observation_bp` — verify blood pressure splits into systolic/diastolic
   - `test_map_observation_hba1c` — verify HbA1c observation mapping
   - `test_map_observation_lipids` — verify lipid panel mapping
   - `test_map_medication_insulin` — verify insulin medication → ContextEvent + metadata
   - `test_map_medication_oral` — verify oral meds → ContextEvent + metadata
   - `test_map_condition_diabetes` — verify diabetes condition → ContextEvent
   - `test_map_condition_comorbidities` — verify comorbidity extraction
   - `test_map_encounter` — verify encounter → ContextEvent mapping
   - `test_map_careplan` — verify careplan → ContextEvent mapping
   - `test_build_synthetic_metadata_completeness` — verify all top-level metadata keys present
   - `test_build_synthetic_metadata_real_time_state` — verify last_* fields populated
   - `test_build_synthetic_metadata_measurements` — verify weight, BP, HbA1c, lipids
   - `test_data_quality_score_calculation` — verify score is between 0 and 1
   - `test_ingest_synthea_directory` — integration test with sample CSV files
   - `test_ingest_simglucose_patient` — test simglucose patient generation
   - `test_error_handling_malformed_row` — verify mapper skips bad rows with logging

5. **Create `tests/test_graph_edge_engine.py`**: New test file for edge generation:
   - `test_load_rules_from_yaml` — verify 20 rules load correctly
   - `test_rule_matching_insulin_glucose` — verify insulin→glucose drop rule fires
   - `test_rule_matching_carb_glucose` — verify carb→glucose spike rule fires
   - `test_rule_matching_exercise_glucose` — verify exercise→glucose drop rule fires
   - `test_all_20_rules_have_valid_structure` — verify YAML schema for all rules
   - `test_temporal_proximity_window` — verify edges only created within 4-hour window
   - `test_exponential_decay_confidence` — verify confidence values at 15min, 60min, 120min, 200min
   - `test_edge_deduplication` — verify no duplicate edges for same source/target/type
   - `test_edge_creation_for_user` — verify edges are persisted to DB
   - `test_condition_led_vs_temporal_split` — verify edge_stats metadata reflects both types

6. **Create `tests/test_synthetic_integration.py`**: New integration test file for full pipeline:
   - `test_full_pipeline_single_patient` — seed one patient end-to-end, verify all phases
   - `test_conversation_agent_rag_with_synthetic` — verify ConversationAgent can retrieve RAG context for a synthetic patient
   - `test_pattern_agent_with_synthetic` — verify PatternAgent can detect patterns in synthetic data
   - `test_safety_agent_with_synthetic` — verify SafetyAgent handles synthetic emergency keywords
   - `test_graph_query_with_synthetic` — verify HealthGraphService returns edges for synthetic patients
   - `test_80_patients_seeded` — verify fixture creates exactly 80 patients
   - `test_all_patients_have_edges` — verify no orphaned patients (all have at least one edge)
   - `test_all_patients_have_metadata` — verify all 80 patients have synthetic_metadata populated
   - `test_validation_report_generation` — verify validate_synthetic_pool.py runs without error

7. **Update `tests/conftest.py`**: Add new fixtures:
   - `synthetic_patient(db_session)` — creates and returns a single fully-seeded synthetic patient with edges and metadata. Uses `SyntheticIngestionMapper` + `GraphEdgeRuleEngine`.
   - `synthetic_pool(db_session)` — creates and returns 80 fully-seeded synthetic patients. Used by integration tests. Should use a transaction that rolls back after the test session.
   - `sample_synthea_csv(tmp_path)` — creates temporary Synthea-format CSV files for mapper tests.

8. **Create test data files**: Create `tests/fixtures/synthea/` with minimal sample CSV files for unit testing:
   - `patients.csv` — 3 sample patients
   - `observations.csv` — 10 sample observations (glucose, weight, BP, HbA1c, lipids)
   - `medications.csv` — 5 sample medications (insulin types, metformin)
   - `conditions.csv` — 5 sample conditions (diabetes, hypertension, retinopathy)
   - `encounters.csv` — 3 sample encounters
   - `careplans.csv` — 2 sample careplans

9. **Run full test suite**: Execute `pytest tests/test_synthetic_ingestion.py tests/test_graph_edge_engine.py tests/test_synthetic_integration.py -v` and verify all tests pass.

10. **Run full project test suite**: Execute `pytest` and verify no regressions in existing tests.

## Verification

- `pytest tests/test_synthetic_ingestion.py -v` — all mapper tests pass (at least 18 tests)
- `pytest tests/test_graph_edge_engine.py -v` — all edge engine tests pass (at least 10 tests)
- `pytest tests/test_synthetic_integration.py -v` — all integration tests pass (at least 9 tests)
- `pytest tests/ -v` — full project test suite passes with no regressions
- `grep -c "def test_" tests/test_synthetic_ingestion.py` returns at least 18
- `grep -c "def test_" tests/test_graph_edge_engine.py` returns at least 10
- `grep -c "def test_" tests/test_synthetic_integration.py` returns at least 9
- Fixtures `synthetic_patient` and `synthetic_pool` are available in `conftest.py`

## Dependencies

- Task #142 (SyntheticIngestionMapper) — tests cover mapper methods
- Task #143 (hybrid metadata storage) — tests query synthetic columns
- Task #144 (GraphEdgeRuleEngine) — tests cover edge generation
- Task #145 (seeding scripts) — integration tests mirror script functionality

## Audit (EOD Report-Back)

Completed by the agent at task completion. Record:
- **Tokens consumed**: approximate total
- **Files changed**: list of modified/created files
- **Stages completed**: which steps were done
- **Stages deferred**: which steps remain (if any)
- **Unexpected issues**: blockers, wrong assumptions, or bugs encountered
- **Artifacts left behind**: temp files, worktrees, debug output
