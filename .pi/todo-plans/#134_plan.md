# Clanker Ops #134: [RESEARCHER] Synthetic user pool from health records

Status: ✅ completed
Owner: @clanker
Tags: #researcher #data #T1D
Branch: research/synthetic-users

## Intended Outcome

Produce a pool of synthetic T1D user profiles that realistically represent health metrics and events extracted from existing data structures, ensuring all PII is removed. These will support simulation and testing pipelines.

## Step-by-Step

1. Inspect `app/db/models.py` to identify relevant schemas (`HealthMetric`, `ContextEvent`, `User`).
2. Create a research script (`research/synthetic_data_exploration.py`) to analyze statistical properties of current T1D metrics (CGM averages, insulin bolus frequency, event correlations).
3. Define a generator protocol in `app/services/synthetic_data_generator.py` that maps these properties to new virtual users.
4. Implement anonymization guardrails in the generation process.
5. Generate a test set of 10-20 virtual users and store in `data/synthetic/`.

## Verification

- Generation script runs without error.
- Synthetic users have realistic metric distributions compared to base data.
- No PII (real user emails, names) present in synthetic data.

## Dependencies

- None.

## Audit (EOD Report-Back)

Completed.
- **Tokens consumed**: ~8k
- **Files changed**: `research/synthetic_data_exploration.py`, `app/services/synthetic_data_generator.py`, `data/synthetic/`
- **Stages completed**: All steps completed.
- **Stages deferred**: None.
- **Unexpected issues**: `ModuleNotFoundError` for pandas, resolved by using virtual environment pip.
- **Artifacts left behind**: Generated synthetic data in `data/synthetic/`.
