# T1D Companion — Sim User Insights Pipeline

A Type 1 Diabetes AI companion that estimates meal carbohydrates with **quantified uncertainty**, asks **targeted clarifying questions** when it matters, and communicates results in **human-friendly language** — all built on a 12-Factor Agent architecture.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Pipeline Stages](#pipeline-stages)
- [Carbohydrate Estimation with Uncertainty](#carbohydrate-estimation-with-uncertainty)
- [Clarification Protocol](#clarification-protocol)
- [Food Search & Scoring](#food-search--scoring)
- [Quick Start](#quick-start)
- [Human Operator Guide](#human-operator-guide)
- [File Layout](#file-layout)
- [Key Design Decisions](#key-design-decisions)
- [Safety](#safety)

---

## Overview

This pipeline simulates a T1D companion that helps users understand the glucose impact of a meal. It follows the [12-Factor Agents](https://github.com/humanlayer/12-factor-agents) principles for testability, debuggability, and replayability.

### Key capabilities

- **Per-food carb ranges**: Every food gets a point estimate AND a plausible range (e.g., "coleslaw ~10g carbs, range 8–15g")
- **Meal-level aggregation**: Sums Per-food ranges into a meal-level uncertainty band (e.g., "about 61g carbs, likely range 50–90g, medium confidence")
- **Targeted clarification**: Only asks questions when uncertainty is clinically meaningful (≥40g meal, ≥20g spread, ≥15g per-food spread)
- **Interactive mode**: Two-way CLI dialogue where the companion asks about portion sizes and refines its estimate
- **Semantic + lexical search**: Combines pgvector embeddings with trigram-indexed ILIKE for fast, accurate food matching
- **Generic food-agnostic scoring**: No hardcoded carb bands per food type — uses data completeness, nutrition consistency, and database typicality

### Why uncertainty matters in T1D

A 20–30g carb counting error can shift post-meal glucose by 70–160 mg/dL for a typical adult with T1D. This system is designed to:
1. Reduce avoidable errors through clarifying questions
2. Be transparent about remaining uncertainty so users can apply their own judgment
3. Never present a single number as ground truth when the data supports a wide range

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CompanionState                            │
│  (unified execution + business state, Factor 5)             │
│                                                             │
│  scenario → foods → evidence_items → totals → forecast      │
│  ↓                                                          │
│  total_carbs_g_range, confidence_overall                    │
│  clarification_needed, clarification_prompt, answer         │
└─────────────────────────────────────────────────────────────┘

Pipeline stages (each is a pure function, Factor 8):

  stage_select_profile  →  stage_parse_foods  →  stage_db_lookup
         ↓                       ↓                      ↓
    Random anchor          LLM + fallback          Food search +
    + CGM reading          food parsing            evidence + ranges
                                                        ↓
                                              stage_decide_clarification
                                                        ↓
                                              [interactive? → ask user]
                                                        ↓
                                              stage_apply_clarification
                                                        ↓
  stage_companion_advice  ←  stage_forecast  ←  (re-run db_lookup)
         ↓
    LLM generates response with:
    - Per-food carb breakdown with ranges
    - Meal-level total with uncertainty band
    - Educational bolus estimate tied to range
    - Glucose forecast and timing
    - Risk flags and monitoring guidance
```

---

## Pipeline Stages

### Stage 1: Profile Selection (`stage_select_profile`)
Selects a simulated user profile from 12 anchor archetypes (well_controlled, high_fat_delayed, insulin_resistant, etc.) and generates a CGM reading with trend, IOB, and basal glucose.

### Stage 2: Food Parsing (`stage_parse_foods`)
Parses natural language meal descriptions into structured `ParsedFood` items using LLM + deterministic regex fallback. Extracts food names, quantities, units, and search terms.

### Stage 3: Database Lookup (`stage_db_lookup`)
Searches OpenFoodFacts (Postgres) for each food, computes nutrition evidence, and aggregates meal-level totals with carb ranges.

**Key outputs per food:**
- `computed`: Point-estimate macros (carbs_g, fat_g, sugars_g, protein_g, kcal)
- `carb_range_g`: (min_g, max_g) across plausible candidates
- `confidence`: "high" | "medium" | "low" based on name-match score

**Key outputs at meal level:**
- `totals`: Summed point-estimate macros
- `total_carbs_g_range`: (sum of mins, sum of maxes)
- `confidence_overall`: high only if all foods high; low if any low; else medium

### Stage 4: Clarification Decision (`stage_decide_clarification`)
Determines whether to ask a clarifying question based on clinical significance and uncertainty thresholds.

### Stage 5: Forecast (`stage_forecast`)
Computes a deterministic glucose forecast using Ornstein-Uhlenbeck drift, Gaussian meal kernels, and per-anchor calibration.

### Stage 6: Companion Advice (`stage_companion_advice`)
Generates the final LLM response incorporating all evidence, ranges, confidence, and any clarification answers.

---

## Carbohydrate Estimation with Uncertainty

### Per-food range computation (`_carb_range_for_candidates`)

For each food, the system:

1. Scores all candidates using `_candidate_score` (0.40 × name_sim + 0.35 × semantic_sim + 0.25 × quality)
2. Selects the "plausible set": top 5 candidates within 70% of the best score
3. Converts each candidate's `carbs_per_100g` to grams using the same `serving_amount()` logic as the point estimate
4. Returns `(min_g, max_g)` across the plausible set

### Quality scoring (`_data_quality_score`)

A food-agnostic score in [0, 1] based on:
- **Data completeness**: brand (+0.15), serving size (+0.10), core macros (+0.05 each), extras (+0.02 each)
- **Nutrition consistency**: estimated calories from macros vs stated calories (±0.10 for consistent, −0.15 for inconsistent)
- **Typicality**: distance from per-name database median (±0.03 for within 2×, −0.05 for outliers)
- **Broken data penalty**: negative values (−0.30), carb-only placeholders (−0.10)

### Name similarity (`_candidate_score`)

Position-aware word matching:
- Query word is the **first word** in the product name → 1.0 (e.g., "Beer" matches "Beer, lager")
- Query word is the **last word** → 0.8 (e.g., "beer" matches "Lager Beer")
- Query word is **mid-name** → 0.5 (e.g., "beer" matches "Root Beer")
- Brand bonus → +0.05

This prevents "Root Beer" from outscoring actual "Beer" when the user types "beer".

### Meal-level aggregation

```python
total_carb_min = sum(ev.carb_range_g[0] for ev in evidence_items)
total_carb_max = sum(ev.carb_range_g[1] for ev in evidence_items)

# Fallback when no range available: ±10% of point estimate
if carb_range_g == (0.0, 0.0) and computed.carbs_g:
    carb_range_g = (carbs_g * 0.9, carbs_g * 1.1)
```

### Overall confidence

```python
if all(c == "high" for c in per_food_confidences):
    confidence_overall = "high"
elif any(c == "low" for c in per_food_confidences):
    confidence_overall = "low"
else:
    confidence_overall = "medium"
```

---

## Clarification Protocol

### When to ask

A clarification question is triggered when ALL of these hold:
1. Meal is clinically significant: `total_carbs_g >= 40g`
2. Meal-level range is wide: `total_carb_max - total_carb_min >= 20g`
3. At least one food has meaningful spread: `carb_range >= 15g`

### What it asks

The system identifies the food with the largest carb range and asks:
> "For the {food_name}, is this more like a small, medium, or large portion?"

### How the answer is applied

The user's answer adjusts the quantity of the most uncertain food:
- "small" / "little" / "light" → quantity × 0.7
- "large" / "big" / "extra" → quantity × 1.3
- "medium" or unrecognized → no change

The quantity update propagates to both the evidence item and `state.foods`, so re-running `stage_db_lookup` picks up the change.

### Interactive flow

```
1. User types meal description
2. Pipeline runs stages 1-3 (profile, parse, DB lookup)
3. System decides if clarification is needed
4. If yes → asks question, applies answer, re-runs DB lookup
5. Pipeline continues to forecast + advice
6. LLM response incorporates the clarification answer:
   "Since you said the rice was a large portion, the carbs are likely
   toward the higher end of the 50–90g range."
```

### Non-interactive mode

When not in interactive mode, the system still computes and communicates ranges. The LLM explains uncertainty without asking questions:
> "This meal is about 88g carbs (likely range 20–157g, medium confidence). Most of the uncertainty is in the sweet and sour chicken — different recipes vary widely."

---

## Food Search & Scoring

### Two-stage candidate generation

1. **Semantic search** (pgvector): Uses sentence-transformers embeddings with HNSW index for similarity matching. Only available when an embedding function is explicitly provided (not loaded at runtime to avoid HF model downloads).

2. **Lexical search** (ILIKE + trigram index): Fast index-assisted filtering using PostgreSQL's GIN trigram index on `product_name`. This is the primary search method.

### ILIKE query strategy

- **Multi-word queries**: AND all words (e.g., "chicken wings" → `ILIKE '%chicken%' AND ILIKE '%wings%'`)
- **Single-word queries**: Uses word-boundary matching to avoid false positives (e.g., "beer" won't match "beer bread")
- **Spelling variants**: UK/US mapping (donut↔doughnut, yoghurt↔yogurt, chips↔crisps, aubergine↔eggplant, courgette↔zucchini)

### Performance

- Per-query latency: 3–10ms (was 4+ seconds with `ORDER BY similarity()`)
- 8-food benchmark: 0.3 seconds total
- Functional index on `LOWER(product_name)` for median queries: 27ms (was 430ms)

---

## Quick Start

### Non-interactive (single shot)

```bash
cd /root/t1d
python3 sim_user_insights/scripts/companion_pipeline_v2.py "jacket potato with baked beans and coleslaw"
```

### Interactive mode (with clarification questions)

```bash
python3 sim_user_insights/scripts/companion_pipeline_v2.py --interactive
# or
python3 sim_user_insights/scripts/companion_pipeline_v2.py -i
```

### Verbose mode (see all internal state)

```bash
python3 sim_user_insights/scripts/companion_pipeline_v2.py "big mac and fries" --verbose
```

### Using the verbose runner script

```bash
./sim_user_insights/run_verbose.sh "chicken wings with coleslaw"
```

### Programmatic usage

```python
import asyncio
from sim_user_insights.scripts.companion_pipeline_v2 import run_companion_pipeline

state = await run_companion_pipeline(
    scenario="jacket potato with baked beans",
    anchor_type="well_controlled"  # optional
)
print(state.response)
print(f"Carbs: {state.totals['carbs_g']}g (range: {state.total_carbs_g_range})")
print(f"Confidence: {state.confidence_overall}")
```

---

## Human Operator Guide

This is the normal way a person runs the companion from the terminal.

### 1. Start from the repo root

```bash
cd /root/t1d
```

The app reads `/root/t1d/.env`. For local LLM parsing, Ollama should be reachable at:

```bash
OLLAMA_BASE_URL=http://192.168.0.211:11434
```

### 2. Run a one-shot meal estimate

Use this when you want a quick answer without follow-up questions:

```bash
python3 sim_user_insights/scripts/companion_pipeline_v2.py "spaghetti bolognese"
```

The output includes:
- simulated profile and CGM context
- estimated carbs and likely carb range
- confidence level
- forecast peak timing
- educational bolus estimate language
- monitoring/risk notes

### 3. Run interactively for portion clarification

Use this for real human-style use, especially when portion size matters:

```bash
python3 sim_user_insights/scripts/companion_pipeline_v2.py -i
```

Example flow:

```text
🥕 T1D Companion
What are you about to eat?
> roast beef, 4 roast potatoes, broccoli, carrots, yorkshire pudding

🤖 For the roast potato, is this more like a small, medium, or large portion?
> small
```

The app then recalculates the meal estimate and prints the final companion response.

### 4. Use verbose mode when debugging

Verbose mode shows each pipeline stage: parsed foods, DB evidence, carb range, forecast, and final response length.

```bash
python3 sim_user_insights/scripts/companion_pipeline_v2.py \
  "jacket potato with baked beans and coleslaw" \
  --verbose
```

Short form:

```bash
python3 sim_user_insights/scripts/companion_pipeline_v2.py "fish and chips" -v
```

### 5. Combine interactive + verbose

Useful when checking why the app asked a particular clarification question:

```bash
python3 sim_user_insights/scripts/companion_pipeline_v2.py -i -v
```

### 6. Common test meals

```bash
python3 sim_user_insights/scripts/companion_pipeline_v2.py "spaghetti bolognese"
python3 sim_user_insights/scripts/companion_pipeline_v2.py "roast beef, 4 roast potatoes, broccoli, carrots, yorkshire pudding"
python3 sim_user_insights/scripts/companion_pipeline_v2.py "jacket potato with baked beans and coleslaw"
python3 sim_user_insights/scripts/companion_pipeline_v2.py "sweet and sour chicken with fried rice"
```

### 7. Expected runtime

A typical run currently takes about **10 seconds** end-to-end. Most time is LLM generation; database food search is fast.

### 8. Important interpretation notes

- This is **educational decision support**, not medical advice.
- Treat carb totals as estimates, especially when the range is wide.
- If a clarification question appears, answer `small`, `medium`, or `large`.
- A wide carb range means portion size or database product matching is uncertain.
- Check CGM after eating; the app is designed to support monitoring, not replace judgement.

---

## File Layout

```
sim_user_insights/
  README.md                          # This file
  REFACTORING_SUMMARY.md             # 12-Factor refactoring notes
  run_verbose.sh                     # Verbose CLI runner
  context/README.md                  # Source data description
  docs/README.md                     # Pipeline documentation (older)
  scripts/
    __init__.py
    companion_pipeline_v2.py         # Main pipeline (stages 1-6 + CLI)
    forecast_engine.py               # Deterministic glucose forecast
    sim_current_reading.py           # CGM reading generator
    build_sim_user_insights.py       # Stage 1: deterministic aggregates
    enrich_sim_users.py              # Stage 2: OF enrichment
    run_structured_companion.py      # Stage 3: full companion (older)
  outputs/
    sim_user_insights.json           # Profile insights
    sim_users_enriched.json          # Enriched with OF data
  architecture-review-*.html         # Architecture review outputs
```

### Key source files (outside sim_user_insights)

```
app/
  t1d_companion/
    local_loop.py                    # Food search, scoring, evidence calculation
    prompts/
      companion_system.txt           # LLM system prompt (updated for uncertainty)
      parser_system.txt              # Food parsing prompt
      safety_rules.txt               # Safety constraints
  food/
    service.py                       # FoodService (DB search, semantic search)
    embedding.py                     # Sentence-transformers embedding (offline only)
    models.py                        # Food, OpenFoodFactsProduct models
  core/
    database.py                      # Postgres connection management
```

---

## Key Design Decisions

### 1. No food-specific carb bands

Earlier versions had hardcoded ranges (e.g., "coleslaw: 3–15 g/100g", "donut: 25–70 g/100g"). These were removed in favor of a generic quality prior that works for ALL foods:
- Data completeness → rewards branded, well-specified products
- Nutrition consistency → penalizes entries where macros don't match calories
- Typicality → rewards values close to the database median for that food name

### 2. ILIKE over similarity() for lexical search

`ORDER BY similarity(product_name, query)` does a parallel seq scan over 2.4M rows (4+ seconds). `ILIKE '%word%'` uses the existing GIN trigram index (3–10ms). The trade-off is less sophisticated ranking, but our quality score compensates.

### 3. Position-aware name matching

"Beer" should match "Lager Beer" (last word, score 0.8) before "Root Beer" (mid-name, score 0.5). This simple rule prevents pathological cases without food-specific logic.

### 4. Clarification only when clinically meaningful

Asking "is this small, medium, or large?" for a 15g side salad is annoying. The system only triggers clarification when the meal is ≥40g carbs AND the range spread is ≥20g. This targets the 20–30g errors that actually matter for T1D dosing.

### 5. Ranges from plausible candidates, not all candidates

The carb range is computed from the top 5 candidates within 70% of the best score — not from all 20+ candidates. This focuses the range on realistic alternatives rather than including garbage matches.

### 6. Stateless reducer pattern

Each pipeline stage is a pure function: `stage(input_state) → output_state`. The `CompanionState` dataclass carries all context. This enables:
- Time-travel debugging (inspect state at any point)
- Replayability (save state to disk, resume later)
- Testability (test each stage independently)

---

## Safety

This system is **educational decision support only**. Key safety principles:

- **Never recommends insulin doses**. Uses "educational estimate" language.
- **Surfaces uncertainty**. Always shows ranges, never hides ambiguity.
- **Monitoring-focused language**. Says "check your CGM at 2 hours" not "take X units".
- **Safety rules filter**. The companion system prompt includes explicit safety constraints.
- **No real patient data**. All profiles are simulated archetypes.

---

## Database Requirements

- PostgreSQL 15+ with pgvector extension
- `openfoodfacts_products` table with columns: `code`, `product_name`, `brands`, `carbs_100g`, `proteins_100g`, `fat_100g`, `energy_kcal_100g`, `serving_size`, `fiber_100g`, `sugars_100g`, `sodium_100g`, `embedding_vec` (halfvec(768))
- Required indexes:
  - `ix_off_products_product_name_trgm` — GIN trigram on `product_name`
  - `ix_off_products_product_name_lower` — btree on `LOWER(product_name)`
  - `idx_openfoodfacts_embedding_hnsw` — HNSW on `embedding_vec`
  - `ix_off_products_nutrition_carbs` — btree on `carbs_100g`

---

## License

See repository root.
