# Sim User Insights Context

This workspace turns existing 90-day simulated meal history into safe, reusable profile insights for the T1D Companion loop.

## Source files

- `data/profile_configs.json` — 12 anchor/profile configs used as simulated user profiles.
- `data/food_history_90d_enhanced.json` — 90-day synthetic meal history, 3,251 rows at creation time.
- `data/food_history_90d.json` — fallback history file with the same schema.
- `data/food_history_edges.json` — derived graph/edge-style history data; not used by the first insights script.

## Scripts

- `scripts/build_sim_user_insights.py` — deterministic aggregates + template-based insights.
- `scripts/enrich_sim_users.py` — enriches history with Postgres OpenFoodFacts nutrition data.

## Current history row shape

Each meal row usually contains:

- `timestamp`
- `anchor_type`
- `food`
- `carb_estimate_g`
- `fat_g`
- `bolus_units` — historical simulator field; do not narrate as advice.
- `prebolus_minutes` — historical simulator field; do not narrate as advice.
- `carb_ratio_used`
- `cgm_impact.expected_peak_delta`
- `cgm_impact.peak_time_minutes`
- `cgm_impact.fat_delay_hours`
- `cgm_impact.exercise_modifier`
- `confidence_score`
- `safety_flags`

## Safety stance

The insight builder may compute historical patterns such as delayed-rise frequency or typical peak window. It must not create dosing instructions. LLM usage, if added, should only rewrite deterministic facts into warmer prose.
