# Clanker Ops #145: [IMPLEMENT] Seeding CLI and validation report scripts

Status: pending
Owner: @clanker
Tags: #implementation #scripts #validation
Branch: research/synthea-ingestion

## Intended Outcome

Two CLI scripts are created: `scripts/seed_synthetic.py` for seeding synthetic patients into the database, and `scripts/validate_synthetic_pool.py` for running the 4-phase validation gate and generating a pool-level metadata report. These scripts make the pipeline reproducible and verifiable by any developer or CI system.

## Step-by-Step

1. **Read source documentation**: Read `docs/research/SYNTHETIC_DATA_PIPELINE.md` — specifically the "Validation Gate" section (4-phase) and the "Setup" section (commands).

2. **Read existing services**: Read `app/services/synthetic_ingestion.py` (mapper methods) and `app/services/graph_edge_engine.py` (edge generation) to understand the ingestion API.

3. **Read existing DB setup**: Read `app/core/database.py` to understand `get_db()` and async session management for standalone scripts.

4. **Create `scripts/__init__.py`**: Empty file to make `scripts/` a Python package.

5. **Create `scripts/seed_synthetic.py`**: CLI script with argparse:
   - `--count N` — total number of patients to seed (default: 80)
   -- `--source {synthea,simglucose,all}` — which source to use (default: all)
   - `--synthea-dir PATH` — path to Synthea CSV output directory (default: `data/raw_synthea/`)
   - `--simglucose-count N` — number of simglucose patients if source=all (default: 30)
   - `--dry-run` — print what would be seeded without writing to DB
   - Flow:
     1. Initialize async DB session
     2. If source is synthea or all: call `SyntheticIngestionMapper.ingest_synthea_directory()`
     3. If source is simglucose or all: generate N simglucose patients via `SyntheticIngestionMapper.ingest_simglucose_patient()`
     4. After each user is ingested, call `GraphEdgeRuleEngine.generate_edges_for_user()`
     5. Print summary: users created, metrics created, edges created, errors encountered

6. **Create `scripts/validate_synthetic_pool.py`**: CLI script with argparse:
   - `--min-quality-score FLOAT` — minimum data_quality_score threshold (default: 0.95)
   - `--output PATH` — output path for pool_metadata.json (default: `data/synthetic/pool_metadata.json`)
   - `--verbose` — print per-patient details
   - Flow:
     1. Initialize async DB session
     2. Query all users WHERE `synthetic_source IS NOT NULL`
     3. **Phase 1 — Unit-level checks**:
        - Verify all 20 rule types are represented in the edge pool
        - Verify temporal proximity edges exist with confidence in [0.3, 0.7]
     4. **Phase 2 — Integration checks**:
        - For a sample of 5 synthetic patients, call `ConversationAgent.handle()` with a test query and verify RAG context retrieval succeeds
        - For a sample of 5 synthetic patients, call `PatternAgent.handle()` and verify pattern detection runs without error
        - Verify `SafetyAgent` correctly handles synthetic emergency keywords
     5. **Phase 3 — Metadata integrity**:
        - Verify every patient has all real-time state fields populated in `synthetic_metadata`
        - Verify `data_quality_score` > threshold for all patients
        - Verify `validation_status` = "passed" for all patients
     6. **Phase 4 — Cross-reference**:
        - For each patient, verify that `last_insulin_injection` timestamp has a corresponding `HealthMetricEdge`
        - Verify glucose forecasts align with actual glucose trend data
        - Verify medication regimen matches medication events in the graph
     7. Generate `pool_metadata.json`:
        ```json
        {
          "generated_at": "ISO timestamp",
          "total_patients": 80,
          "synthea_count": 50,
          "simglucose_count": 30,
          "total_metrics": N,
          "total_edges": N,
          "condition_led_edges": N,
          "temporal_proximity_edges": N,
          "avg_data_quality_score": 0.98,
          "patients_passed": 80,
          "patients_failed": 0,
          "edge_type_distribution": {"INSULIN_TO_GLUCOSE_DROP": 120, ...},
          "glucose_profile_distribution": {"well-controlled": 30, "high-variability": 35, "frequent-hypo": 15},
          "rule_coverage": {"rules_fired": 20, "rules_missed": 0},
          "validation_phases_passed": 4,
          "seed_version": "1.0.0"
        }
        ```
     8. Print summary report to stdout

7. **Add `scripts/` to `pyproject.toml`**: Ensure the scripts directory is recognized. Add entry point if needed.

8. **Add `data/synthetic/` to `.gitignore`**: Ensure generated synthetic data is not committed to version control (but `pool_metadata.json` may be committed for reference).

## Verification

- `python -m scripts.seed_synthetic --count 5 --dry-run` prints seeding plan without DB writes
- `python -m scripts.seed_synthetic --count 5` seeds 5 test patients successfully
- `python -m scripts.validate_synthetic_pool --verbose` runs all 4 phases and prints report
- `data/synthetic/pool_metadata.json` is generated with all required top-level keys
- Script handles edge cases: empty DB (no synthetic patients), partial seeding, malformed metadata

## Dependencies

- Task #142 (SyntheticIngestionMapper) — scripts call mapper methods
- Task #143 (hybrid metadata storage) — scripts query synthetic columns
- Task #144 (GraphEdgeRuleEngine) — validation script checks edge generation
- Synthea CSV files must exist in `data/raw_synthea/` before seeding

## Audit (EOD Report-Back)

Completed by the agent at task completion. Record:
- **Tokens consumed**: approximate total
- **Files changed**: list of modified/created files
- **Stages completed**: which steps were done
- **Stages deferred**: which steps remain (if any)
- **Unexpected issues**: blockers, wrong assumptions, or bugs encountered
- **Artifacts left behind**: temp files, worktrees, debug output
