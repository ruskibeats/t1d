# Synthetic Data Pipeline for T1D Companion

*Created: 2026-05-20*
*Task: #141*
*Status: In Progress*

---

## Overview

This document describes the synthetic data ingestion pipeline for the T1D Companion. The pipeline generates realistic synthetic T1D patient profiles and ingests them into the system's database and knowledge graph, enabling testing of the RAG pipeline, pattern detection, conversational agent, and safety systems without using real patient data.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYNTHETIC DATA PIPELINE                       │
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │ Synthea   │    │ simglucose   │    │  Other Sources        │  │
│  │ (50 pts)  │    │ (30 pts)     │    │  (Pioneer, Kaggle)    │  │
│  └────┬─────┘    └──────┬───────┘    └───────────┬───────────┘  │
│       │                 │                        │              │
│       └────────────┬────┴────────────────────────┘              │
│                    ▼                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           SyntheticIngestionMapper                        │    │
│  │  • Maps CSV/FHIR → User, HealthMetric, ContextEvent      │    │
│  │  • Extracts rich metadata (real-time state, history)     │    │
│  │  • Assigns glucose profile & data quality scores         │    │
│  └──────────────────────┬──────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           GraphEdgeRuleEngine                             │    │
│  │  • 20 condition-led rules (YAML config)                  │    │
│  │  • Temporal proximity heuristic (4h, exp decay 0.3-0.7)  │    │
│  │  • Creates HealthMetricEdge entries                       │    │
│  └──────────────────────┬──────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           PostgreSQL Database                             │    │
│  │  • tbl_users (core columns + synthetic_metadata JSON)    │    │
│  │  • tbl_health_metrics (via HealthMetric model)           │    │
│  │  • tbl_context_events (via ContextEvent model)           │    │
│  │  • tbl_health_metric_edges (graph relationships)         │    │
│  └──────────────────────┬──────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           Validation & Reporting                          │    │
│  │  • 4-phase validation gate                               │    │
│  │  • Cross-reference checks (metadata ↔ graph edges)       │    │
│  │  • Pool-level metadata (pool_metadata.json)              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Sources

### Primary: Synthea

- **Patients**: 50
- **Format**: CSV (patients, observations, medications, conditions, encounters, careplans)
- **Strengths**: Full longitudinal patient histories, realistic clinical timelines
- **Setup**: Requires JDK (see [Setup](#setup))

### Secondary: simglucose

- **Patients**: 30 (10 adolescent, 10 adult, 10 child)
- **Format**: Python API → generated programmatically
- **Strengths**: Physics-based UVA/Padovo simulator, 5-minute CGM intervals, full meal/insulin/exercise data
- **Setup**: `pip install simglucose`

### Future Sources

| Source | Use Case | Patients |
|--------|----------|----------|
| Pioneer Data Hub | UK-style hospital admissions | ~159,800 |
| Kaggle | Quick ML/test datasets | Varies |
| HuggingFace | Pre-built synthetic datasets | Varies |
| SDV/CTGAN/TVAE | Custom generation from seed data | Custom |

---

## Metadata Schema

### Storage: Hybrid Approach

**Core queryable columns** on `tbl_users`:
- `synthetic_id` — unique identifier
- `diabetes_type` — Type 1 / Type 2 / prediabetes
- `age_range` — child / adolescent / adult / elderly
- `expected_glucose_profile` — well-controlled / high-variability / frequent-hypo
- `data_quality_score` — 0-1 completeness metric
- `validation_status` — passed / failed
- `source` — synthea / simglucose / manual
- `seed_version` — version of rules/config used

**JSON blob** (`synthetic_metadata`): Full rich metadata set.

### Per-Patient Metadata Fields

#### Demographics
| Field | Type | Description |
|-------|------|-------------|
| `synthetic_id` | string | Unique identifier |
| `age` | int | Age in years |
| `sex` | string | M/F |
| `ethnicity` | string | Ethnicity |
| `location` | string | Geographic location |
| `deprivation_index` | float | Socioeconomic index |

#### Clinical
| Field | Type | Description |
|-------|------|-------------|
| `diabetes_type` | string | Type 1 / Type 2 / prediabetes |
| `diagnosis_date` | datetime | Date of diagnosis |
| `hba1c_history` | list | Timeline of HbA1c values |
| `bmi_history` | list | Timeline of BMI values |
| `comorbidities` | list | Conditions with onset dates |
| `medication_regimen` | object | Insulin types, doses, frequencies |
| `allergies` | list | Known allergies |
| `family_history` | list | Relevant family history |

#### Glucose Profile
| Field | Type | Description |
|-------|------|-------------|
| `expected_glucose_profile` | string | well-controlled / high-variability / frequent-hypo |
| `cgm_coverage_percent` | float | % of time with CGM data |
| `time_in_range_target` | float | Target TIR percentage |
| `avg_glucose` | float | Average glucose value |
| `glucose_variability_cv` | float | Coefficient of variation |

#### Lifestyle (Daily Patterns)
| Field | Type | Description |
|-------|------|-------------|
| `meal_times` | object | Breakfast/lunch/dinner/snack timestamps |
| `avg_daily_calories` | float | Average daily caloric intake |
| `carb_intake_grams_avg` | float | Average daily carb intake |
| `exercise_frequency` | int | Times per week |
| `exercise_type` | string | Primary exercise type |
| `exercise_duration_avg` | int | Average duration in minutes |
| `sleep_hours_avg` | float | Average sleep hours |
| `sleep_quality_score` | float | 0-100 sleep quality |
| `bedtime` | time | Typical bedtime |
| `wake_time` | time | Typical wake time |
| `stress_level_avg` | float | 0-10 stress level |
| `work_schedule` | string | day / shift / irregular |

#### Real-Time State
| Field | Type | Description |
|-------|------|-------------|
| `last_insulin_injection` | object | {timestamp, type, units} |
| `last_carb_intake` | object | {timestamp, grams, meal_type} |
| `last_glucose_reading` | object | {timestamp, value, trend_direction} |
| `last_drink` | object | {timestamp, type, volume_ml} |
| `last_exercise` | object | {timestamp, type, duration_min, intensity} |
| `last_sleep_end` | object | {timestamp, sleep_duration_hours, sleep_score} |
| `last_mood_entry` | object | {timestamp, mood_score, notes} |
| `last_hypo_event` | object | {timestamp, severity, treatment} |
| `last_hyper_event` | object | {timestamp, value, correction_given} |
| `glucose_forecast_1h` | float | Predicted glucose in 1 hour |
| `glucose_forecast_3h` | float | Predicted glucose in 3 hours |

#### Current Measurements
| Field | Type | Description |
|-------|------|-------------|
| `weight_kg` | float | Current weight |
| `height_cm` | float | Current height |
| `bmi` | float | Calculated BMI |
| `blood_pressure_systolic` | int | Most recent systolic BP |
| `blood_pressure_diastolic` | int | Most recent diastolic BP |
| `heart_rate_resting` | int | Resting heart rate |
| `hba1c_most_recent` | object | {value, date} |
| `lipid_panel` | object | {total_cholesterol, hdl, ldl, triglycerides, date} |
| `egfr` | object | {value, date} — kidney function |
| `thyroid_tsh` | object | {value, date} |

#### Active Context (Today So Far)
| Field | Type | Description |
|-------|------|-------------|
| `current_cgm_sensor_age_days` | int | Days since sensor inserted |
| `current_insulin_pump_cartridge_remaining_units` | float | Remaining insulin |
| `active_medications` | list | With last taken timestamps |
| `today_so_far` | object | {carbs_consumed, insulin_delivered, glucose_avg, time_in_range} |

#### Technical
| Field | Type | Description |
|-------|------|-------------|
| `source` | string | synthea / simglucose / manual |
| `seed_version` | string | Version of rules/config |
| `generation_timestamp` | datetime | When this patient was generated |
| `data_quality_score` | float | 0-1 completeness |
| `edge_stats` | object | {condition_led_count, temporal_proximity_count, total} |
| `validation_status` | string | passed / failed |
| `notes_clinical_summary` | string | Free-text clinical summary |

---

## Graph Edge Rules

### Condition-Led Rules (20 rules, YAML-configured)

Rules are defined in `config/graph_edge_rules.yaml`. Each rule specifies:
- `source_pattern`: Metric/event type to match
- `target_pattern`: Metric/event type to match
- `edge_type`: The `GraphEdgeType` to create
- `confidence`: Base confidence score (0-1)
- `time_delay_minutes`: Expected delay between source and target
- `clinical_rationale`: Human-readable explanation

### Initial 20 Rules

| # | Source | Target | Edge Type | Confidence | Delay (min) |
|---|--------|--------|-----------|------------|-------------|
| 1 | insulin_administration | glucose_decrease | INSULIN_TO_GLUCOSE_DROP | 0.85 | 30-120 |
| 2 | carb_intake | glucose_increase | MEAL_TO_GLUCOSE_SPIKE | 0.90 | 15-60 |
| 3 | exercise | glucose_decrease | EXERCISE_TO_GLUCOSE_DROP | 0.70 | 0-240 |
| 4 | stress_event | glucose_increase | STRESS_TO_GLUCOSE_RISE | 0.60 | 15-90 |
| 5 | illness_onset | glucose_increase | ILLNESS_TO_GLUCOSE_RISE | 0.75 | 60-480 |
| 6 | sleep_onset | glucose_stabilization | SLEEP_TO_GLUCOSE_STABLE | 0.50 | 120-480 |
| 7 | alcohol_intake | glucose_decrease | ALCOHOL_TO_GLUCOSE_DROP | 0.65 | 60-240 |
| 8 | menstrual_cycle_phase | glucose_variability | HORMONE_TO_GLUCOSE_VAR | 0.55 | 0-1440 |
| 9 | medication_change | glucose_trend_change | MED_CHANGE_TO_GLUCOSE | 0.70 | 1440-4320 |
| 10 | high_fat_meal | delayed_glucose_spike | FAT_TO_DELAYED_SPIKE | 0.75 | 120-360 |
| 11 | caffeine_intake | glucose_increase | CAFFEINE_TO_GLUCOSE_RISE | 0.45 | 15-60 |
| 12 | dehydration | glucose_increase | DEHYDRATION_TO_GLUCOSE | 0.50 | 60-240 |
| 13 | high_glucose | correction_insulin | HYPER_TO_CORRECTION | 0.80 | 5-30 |
| 14 | low_glucose | carb_treatment | HYPO_TO_TREATMENT | 0.85 | 5-15 |
| 15 | dawn_phenomenon | glucose_increase | DAWN_TO_GLUCOSE_RISE | 0.70 | 120-360 |
| 16 | somogyi_effect | glucose_rebound | SOMOGYI_TO_REBOUND | 0.60 | 240-480 |
| 17 | exercise_intensity_high | glucose_increase | INTENSE_EXERCISE_TO_HYPER | 0.55 | 0-30 |
| 18 | sleep_poor_quality | glucose_variability | POOR_SLEEP_TO_VAR | 0.50 | 240-480 |
| 19 | travel_timezone_change | glucose_disruption | TRAVEL_TO_DISRUPTION | 0.45 | 480-1440 |
| 20 | steroid_medication | glucose_increase | STEROID_TO_GLUCOSE_RISE | 0.80 | 120-480 |

### Temporal Proximity Heuristic

For metric pairs not covered by condition-led rules:

- **Window**: 4 hours (240 minutes)
- **Confidence decay**: Exponential
  - 0-30 min: 0.70
  - 30-60 min: 0.55
  - 60-120 min: 0.40
  - 120-240 min: 0.30
- **Minimum confidence threshold**: 0.30 (edges below this are discarded)

---

## Validation Gate

### Phase 1: Unit Tests
- `SyntheticIngestionMapper` correctly maps all CSV columns to domain models
- `GraphEdgeRuleEngine` correctly applies all 20 condition-led rules
- Temporal proximity heuristic produces edges within expected confidence range
- All metadata fields are populated for every patient

### Phase 2: Integration Verification
- 80 patients seeded with zero errors
- Validation report confirms: patient count, metric count, edge count, no orphans
- `ConversationAgent` can retrieve RAG context for a synthetic patient
- `PatternAgent` can detect patterns in synthetic data
- `SafetyAgent` correctly handles synthetic emergency keywords

### Phase 3: Metadata Integrity
- Every patient has all real-time state fields populated
- `data_quality_score` > 0.95 for all patients
- `validation_status` = "passed" for all 80
- Pool-level metadata file is generated and accurate

### Phase 4: Cross-Reference Validation
- Edges in graph are consistent with metadata
- If metadata says `last_insulin_injection` was 30 min ago, a corresponding edge exists
- Glucose forecasts align with actual glucose trend data
- Medication regimen matches medication events in the graph

---

## Setup

### Prerequisites

```bash
# Install JDK (required for Synthea)
apt install default-jdk

# Install simglucose
pip install simglucose

# Install Synthea
git clone https://github.com/synthetichealth/synthea.git tools/synthea
cd tools/synthea
./gradlew build check test -x test
```

### Generating Synthetic Data

```bash
# Generate 50 diabetes-focused patients with Synthea
cd tools/synthea
./run_synthea -p 50 -m diabetes --exporter.csv.export true -o ../../data/raw_synthea/

# Generate 30 simglucose patients
python -m scripts.generate_simglucose --count 30 --output data/raw_simglucose/
```

### Seeding the Database

```bash
# Seed all 80 patients (50 Synthea + 30 simglucose)
python -m scripts.seed_synthetic --count 80

# Or seed individually
python -m scripts.seed_synthetic --source synthea --count 50
python -m scripts.seed_synthetic --source simglucose --count 30
```

### Running Validation

```bash
# Full validation report
python -m scripts.validate_synthetic_pool

# Output: data/synthetic/pool_metadata.json
```

---

## File Structure

```
t1d-companion/
├── app/
│   ├── services/
│   │   ├── synthetic_ingestion.py      # SyntheticIngestionMapper
│   │   └── graph_edge_engine.py        # GraphEdgeRuleEngine
│   └── db/
│       └── models.py                    # Updated User model (hybrid metadata)
├── config/
│   └── graph_edge_rules.yaml            # 20 condition-led rules
├── data/
│   ├── raw_synthea/                     # Synthea CSV output
│   ├── raw_simglucose/                  # simglucose generated data
│   └── synthetic/                       # Processed synthetic data
│       └── pool_metadata.json           # Pool-level metadata
├── scripts/
│   ├── seed_synthetic.py                # CLI seeding command
│   ├── generate_simglucose.py           # simglucose generator
│   └── validate_synthetic_pool.py       # Validation report
├── tests/
│   ├── test_synthetic_ingestion.py      # Mapper unit tests
│   ├── test_graph_edge_engine.py        # Edge engine unit tests
│   └── test_synthetic_integration.py    # Full pipeline integration tests
└── docs/
    └── research/
        └── SYNTHETIC_DATA_PIPELINE.md   # This file
```

---

## References

- [Synthea](https://github.com/synthetichealth/synthea) — Synthetic patient generator
- [simglucose](https://github.com/jxx123/simglucose) — UVA/Padova T1D simulator
- [Pioneer Data Hub](https://www.pioneerdatahub.org/) — UK synthetic diabetes admissions
- [Diabetes Data Sources](DIABETES_DATA_SOURCES.md) — Previous research on data sources
- [Graph Edge Detection](graph-edge-wiring-pattern-detection) — Existing edge wiring patterns
