# Sim User Insights Pipeline

## Purpose

Structured insight layer for simulated T1D users with 90-day meal history. Every number comes from code or Postgres — LLM only writes assessment and advice prose.

## Pipeline Stages

### Stage 0: Profile configs (`data/profile_configs.json`)
Full PatientConfig parameters (basal glucose, meal rise factor, carb ratio, insulin sensitivity, fat delay, etc.) generated from 12 anchor archetypes. Used as the sim user base.

### Stage 1: Deterministic aggregates (`scripts/build_sim_user_insights.py`)
- Groups 90-day history by anchor type
- Computes: meal count, common foods, carb/fat/peak/confidence distributions
- Detects patterns: delayed-rise tendency, high-carb frequency, higher-fat context
- Writes `outputs/sim_user_insights.json`

### Stage 2: OpenFoodFacts enrichment (`scripts/enrich_sim_users.py`)
- Queries Postgres `openfoodfacts_products` for each unique food in history
- Derives serving sizes, computes real macros from OF per-100g values
- Cross-references historical carb/fat estimates against OF-computed values
- Writes `outputs/sim_users_enriched.json`

### Stage 3: Structured companion (`scripts/run_structured_companion.py`)
- Parses scenario (fallback + LLM enrichment)
- Selects anchor profile with full clinical params
- Looks up foods in Postgres OpenFoodFacts
- Finds similar historical meals from 90-day history (deduplicated by food name)
- Computes deterministic glucose forecast (OU drift, Gaussian kernels, balance factor per anchor)
- LLM generates assessment + companion advice (post-processed: first sentence = assessment, rest = advice)
- Safety filter checks for forbidden phrasing
- Outputs 7 structured sections

## Forecast model (maths-skills compliant)

- Ornstein-Uhlenbeck drift (rate 0.015/min) pulling toward basal
- Wider starch Gaussian (σ=50) for proper overlap with insulin window
- Balance factor per anchor: well_controlled=1.2, high_fat_delayed=1.35, post_meal_spike=2.0, etc.
- 5-minute timestepping for temporal accuracy
- Per-anchor calibrated rise (0.5-0.9 mg/dL per gram carb, not the raw simulator meal_rise_factor)

## Quick eval

```bash
# Single anchor run
python3 scripts/run_openrouter_companion_eval.py --anchor high_fat_delayed

# Full structured companion
python3 sim_user_insights/scripts/run_structured_companion.py
```

## File layout

```
sim_user_insights/
  context/README.md          -- Source data description
  docs/README.md             -- This file
  scripts/
    build_sim_user_insights.py   -- Stage 1: deterministic aggregates
    enrich_sim_users.py          -- Stage 2: OF enrichment
    run_structured_companion.py  -- Stage 3: full companion
  outputs/
    sim_user_insights.json       -- Stage 1 output
    sim_users_enriched.json      -- Stage 2 output

scripts/
  run_openrouter_companion_eval.py  -- Quick model eval with enriched data

data/
  profile_configs.json              -- 12 profiles with full PatientConfig
  food_history_90d_enhanced.json    -- 3,251 synthetic meal entries
```