# Clanker Ops #142: [IMPLEMENT] SyntheticIngestionMapper full metadata extraction

Status: pending
Owner: @clanker
Tags: #implementation #data #synthetic
Branch: research/synthea-ingestion

## Intended Outcome

`app/services/synthetic_ingestion.py` is expanded from its current stub (3 basic methods) into a full metadata extraction service that maps Synthea CSV output and simglucose programmatic output into the T1D domain models (`User`, `HealthMetric`, `ContextEvent`) while extracting and attaching the complete rich metadata set defined in `docs/research/SYNTHETIC_DATA_PIPELINE.md`. The mapper must handle all Synthea CSV files (patients, observations, medications, conditions, encounters, careplans) and produce a `synthetic_metadata` JSON dict per user covering demographics, clinical, glucose profile, lifestyle, real-time state, measurements, active context, and technical fields.

## Step-by-Step

1. **Read source documentation**: Read `docs/research/SYNTHETIC_DATA_PIPELINE.md` (full metadata schema, Section "Metadata Schema") and `docs/research/DIABETES_DATA_SOURCES.md` (data source field mappings).

2. **Read existing mapper**: Read `app/services/synthetic_ingestion.py` to understand current stub methods (`map_patient`, `map_observation`, `map_condition`).

3. **Read existing models**: Read `app/db/models.py` (User model columns), `app/metrics/schemas.py` (HealthMetricCreate), and `app/metrics/types.py` (MetricType enum) to understand target schema.

4. **Implement `map_patient` expansion**: Update `map_patient(row)` to extract from Synthea `patients.csv`:
   - `Id` → `synthetic_id`
   - `FIRST`, `LAST` → `full_name`, `email`
   - `BIRTHDATE` → calculate `age`, assign `age_range` (child <13, adolescent 13-17, adult 18-64, elderly 65+)
   - `GENDER` → `sex`
   - `RACE`, `ETHNICITY` → store in metadata
   - `ADDRESS` → parse `location`, estimate `deprivation_index`
   - Set `hashed_password` to a bcrypt-hashed placeholder
   - Set `diabetes_type` based on conditions (default "Type 1" for biased cohort)

5. **Implement `map_observation` expansion**: Update `map_observation(row, user_id)` to handle all Synthea `observations.csv` types, not just glucose:
   - `Glucose` / `Blood Glucose` → `HealthMetric` (type=BLOOD_GLUCOSE)
   - `Body Weight` → `HealthMetric` (type=WEIGHT_KG) + update metadata `weight_kg`
   - `Body Height` → `HealthMetric` (type=HEIGHT_CM) + update metadata `height_cm`
   - `Heart Rate` → `HealthMetric` (type=HEART_RATE) + update metadata `heart_rate_resting`
   - `Blood Pressure` → split into systolic/diastolic `HealthMetric` entries
   - `HbA1c` → `HealthMetric` (type=HBA1C) + update metadata `hba1c_most_recent`
   - `Cholesterol`, `HDL`, `LDL`, `Triglycerides` → `HealthMetric` entries + update `lipid_panel`
   - `eGFR` → `HealthMetric` + update metadata `egfr`
   - `TSH` → `HealthMetric` + update metadata `thyroid_tsh`
   - Track `last_glucose_reading` in metadata (most recent glucose observation)

6. **Implement `map_medication` (new)**: Create `map_medication(row, user_id)` for Synthea `medications.csv`:
   - Map to `ContextEvent` (event_type="medication")
   - Extract insulin types (rapid-acting, long-acting) → update `medication_regimen` in metadata
   - Track `last_insulin_injection` (most recent insulin medication)
   - Track oral meds (metformin, GLP-1) → update `active_medications` in metadata
   - Track `last_hypo_event` treatment medications (glucose tablets, glucagon)

7. **Implement `map_condition` expansion**: Update `map_condition(row, user_id)` for Synthea `conditions.csv`:
   - Map to `ContextEvent` (event_type="condition")
   - Extract comorbidities (hypertension, retinopathy, neuropathy, CKD) → update `comorbidities` list in metadata
   - Set `diagnosis_date` from `START` field
   - Track `last_hyper_event` and `last_hypo_event` from condition descriptions

8. **Implement `map_encounter` (new)**: Create `map_encounter(row, user_id)` for Synthea `encounters.csv`:
   - Map to `ContextEvent` (event_type="encounter")
   - Track `appointment_attendance_rate` in metadata
   - Track `work_schedule` from encounter patterns (regular hours vs. shift work)

9. **Implement `map_careplan` (new)**: Create `map_careplan(row, user_id)` for Synthea `careplans.csv`:
   - Map to `ContextEvent` (event_type="careplan")
   - Update `notes_clinical_summary` from careplan descriptions

10. **Implement `build_synthetic_metadata` (new)**: Create `_build_synthetic_metadata(user_id)` that assembles the full JSON blob:
    - Demographics: `synthetic_id`, `age`, `sex`, `ethnicity`, `location`, `deprivation_index`
    - Clinical: `diabetes_type`, `diagnosis_date`, `hba1c_history`, `bmi_history`, `comorbidities`, `medication_regimen`, `allergies`, `family_history`
    - Glucose Profile: `expected_glucose_profile` (classify from glucose distribution), `cgm_coverage_percent`, `time_in_range_target`, `avg_glucose`, `glucose_variability_cv`
    - Lifestyle: `meal_times`, `avg_daily_calories`, `carb_intake_grams_avg`, `exercise_frequency`, `exercise_type`, `exercise_duration_avg`, `sleep_hours_avg`, `sleep_quality_score`, `bedtime`, `wake_time`, `stress_level_avg`, `work_schedule`
    - Real-Time State: `last_insulin_injection`, `last_carb_intake`, `last_glucose_reading`, `last_drink`, `last_exercise`, `last_sleep_end`, `last_mood_entry`, `last_hypo_event`, `last_hyper_event`, `glucose_forecast_1h`, `glucose_forecast_3h`
    - Measurements: `weight_kg`, `height_cm`, `bmi`, `blood_pressure_systolic`, `blood_pressure_diastolic`, `heart_rate_resting`, `hba1c_most_recent`, `lipid_panel`, `egfr`, `thyroid_tsh`
    - Active Context: `current_cgm_sensor_age_days`, `current_insulin_pump_cartridge_remaining_units`, `active_medications`, `today_so_far`
    - Technical: `source`, `seed_version`, `generation_timestamp`, `data_quality_score`, `edge_stats`, `validation_status`, `notes_clinical_summary`

11. **Implement `ingest_synthea_directory` (new)**: Create `async def ingest_synthea_directory(db, directory: str)` that:
    - Reads all CSV files from `data/raw_synthea/`
    - Calls the appropriate mapper method for each row
    - Calls `_build_synthetic_metadata` after all rows for a user are processed
    - Returns list of created user IDs

12. **Implement `ingest_simglucose_patient` (new)**: Create `async def ingest_simglucose_patient(db, patient_config: dict)` that:
    - Accepts simglucose patient config (from `simglucose` Python API)
    - Generates CGM time series, meal events, insulin events
    - Maps to same domain models and metadata structure as Synthea
    - Sets `source` = "simglucose"

13. **Add error handling**: Wrap all mapper methods in try/except with logging via `app.core.logging_config.get_logger`. Skip malformed rows, log warnings, continue processing.

14. **Add `data_quality_score` calculation**: After building metadata, calculate completeness as (populated_fields / total_fields). Store in `data_quality_score`.

## Verification

- `grep -c "async def" app/services/synthetic_ingestion.py` returns at least 8 methods (map_patient, map_observation, map_medication, map_condition, map_encounter, map_careplan, _build_synthetic_metadata, ingest_synthea_directory, ingest_simglucose_patient)
- `pytest tests/test_synthetic_ingestion.py` passes (existing tests still green)
- Manual test: place sample Synthea CSV files in `data/raw_synthea/`, run `ingest_synthea_directory`, verify `User.synthetic_metadata` is populated with all expected top-level keys
- Verify `data_quality_score` is between 0 and 1 for all ingested users

## Dependencies

- Task #143 (hybrid metadata storage) — the `synthetic_metadata` JSON column must exist on `tbl_users` before the mapper can store the blob. Run migration from #143 first.
- Synthea CSV files must exist in `data/raw_synthea/` (generated externally or via `tools/synthea`)
- `simglucose` package installed (`pip install simglucose`)

## Audit (EOD Report-Back)

Completed by the agent at task completion. Record:
- **Tokens consumed**: approximate total
- **Files changed**: list of modified/created files
- **Stages completed**: which steps were done
- **Stages deferred**: which steps remain (if any)
- **Unexpected issues**: blockers, wrong assumptions, or bugs encountered
- **Artifacts left behind**: temp files, worktrees, debug output
