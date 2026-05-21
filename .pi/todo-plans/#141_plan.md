# Clanker Ops #141: [RESEARCHER] Synthetic user pool from health records

Status: in_progress
Owner: @clanker
Tags: #researcher #data #T1D #synthetic
Branch: research/synthea-ingestion

## Intended Outcome

Implement an end-to-end synthetic data ingestion pipeline using Synthea (50 patients) + simglucose (30 patients). Includes rich metadata (real-time state, measurements, lifestyle), hybrid graph edge generation (20 condition-led rules + temporal proximity), 4-phase validation gate, and full documentation.

## Design Decisions (from grill-me session)

- **Sources**: Synthea (primary, 50 pts) + simglucose (secondary, 30 pts) = 80 total
- **Edge generation**: Hybrid — 20 condition-led rules (YAML config) + temporal proximity (4h window, exponential decay 0.3-0.7)
- **Metadata storage**: Hybrid — core queryable columns + JSON blob on User model
- **Real-time state**: Last insulin, carbs, glucose, drink, exercise, sleep, mood, hypo/hyper events, glucose forecasts
- **Measurements**: Weight, BP, HR, HbA1c, lipids, eGFR, thyroid
- **Validation**: 4-phase gate — Unit → Integration → Metadata Integrity → Cross-reference
- **Documentation**: docs/research/SYNTHETIC_DATA_PIPELINE.md

## Sub-Tasks

| ID | Task | Status |
|----|------|--------|
| #142 | Implement SyntheticIngestionMapper for full metadata extraction | pending |
| #143 | Add hybrid metadata storage to User model | pending |
| #144 | Implement GraphEdgeRuleEngine with 20 rules + temporal proximity | pending |
| #145 | Create seeding CLI and validation report scripts | pending |
| #146 | Write tests and create 80-patient test fixture | pending |

## Verification

- `pytest tests/test_synthetic_ingestion.py` passes
- `pytest tests/test_graph_edge_engine.py` passes
- `pytest tests/test_synthetic_integration.py` passes
- `python -m scripts.validate_synthetic_pool` reports 80 patients, all passed
- All 80 patients have data_quality_score > 0.95
- Cross-reference validation passes (metadata ↔ graph edges consistent)

## Dependencies

- JDK (for Synthea)
- simglucose (`pip install simglucose`)

## Audit (EOD Report-Back)

- **Documentation**: Completed — docs/research/SYNTHETIC_DATA_PIPELINE.md
- **Implementation**: In progress — see sub-tasks #142-146
