# Local T1D Companion Loop — Design Brief
**Date:** 2026-05-23

## Objective

Build an entirely local T1D companion interaction loop for scenario questions such as:

> "I want to eat 2 donuts and 3 cans of coke — what will likely happen?"

The system should:

1. Pick a random simulated T1D user/profile.
2. Use a local LLM only for natural-language interpretation and final companion wording.
3. Search the local PostgreSQL/OpenFoodFacts database for nutritional evidence.
4. Calculate nutrition and T1D effects deterministically in code.
5. Return a safety-compliant companion-style response grounded in local data.

The model must **not** invent carb values. Numeric nutrition must come from local data and code.

---

## Current Project State

The project already has the core pieces:

### Existing code

- `app/t1d_companion/fast_analysis.py`
  - Existing meal-analysis entry point.
  - Has quantity/unit parsing.
  - Has optional Ollama path.
  - Has `analyze_meal()` using `FoodService._search_local_off()`.

- `app/food/service.py`
  - Has `_search_local_off(query, limit=5)`.
  - Searches `openfoodfacts_products` using PostgreSQL trigram similarity.
  - Returns normalized nutrition fields:
    - `carbs_per_100g`
    - `fat_per_100g`
    - `protein_per_100g`
    - `calories_per_100g`
    - `serving_size`
    - `sugars_per_100g`
    - `fiber_per_100g`

- `app/simulator/patient_factory.py`
  - Generates simulated T1D patient profiles.
  - Supports multiple `AnchorType` profiles.

- `data/profile_configs.json`
  - Cached profile configs used by `fast_analysis.py`.

- `data/food_history_90d.json` and `data/food_history_90d_enhanced.json`
  - Historical/simulated meal outcomes with carb estimates, bolus units, profile type, and CGM impact.

### Local data

- PostgreSQL database: `t1d_companion`
- Table: `openfoodfacts_products`
- Current count: ~2.5M rows
- Source files also available:
  - `data/openfoodfacts/openfoodfacts.parquet`
  - `data/openfoodfacts/openfoodfacts-products.jsonl.gz`

### Local LLM

Ollama endpoint:

```text
http://192.168.0.62:11434
```

Known useful model:

```text
llama3.1:latest
```

The local model should be used as:

- parser / normaliser
- search-term generator
- final-response writer

It should **not** be used as the nutrition source of truth.

---

## Required End-to-End Flow

```text
User scenario
  ↓
Local LLM parses scenario to structured JSON
  ↓
Python selects random simulated T1D profile
  ↓
Python searches local PostgreSQL/OpenFoodFacts for each food item
  ↓
Python chooses/records candidate food matches and nutrition confidence
  ↓
Python calculates carbs/fat/sugar/calories deterministically
  ↓
Python finds similar historical/simulated meals if possible
  ↓
Local LLM receives structured evidence bundle
  ↓
Local LLM writes companion explanation using only provided numbers
```

---

## Proposed Structured JSON From Local LLM

For input:

```text
I want to eat 2 donuts and 3 cans of coke — what will likely happen?
```

The parser should return only JSON:

```json
{
  "intent": "meal_scenario",
  "time_context": null,
  "foods": [
    {"item": "donut", "quantity": 2, "unit": null, "search_terms": ["donut", "doughnut"]},
    {"item": "coke", "quantity": 3, "unit": "can", "search_terms": ["coca cola", "coke", "cola"]}
  ],
  "modifiers": {
    "exercise": null,
    "alcohol": null,
    "temperature": null
  },
  "question": "what will likely happen"
}
```

If the model fails to return valid JSON, code should fall back to deterministic regex parsing.

---

## Database Search Rules

Do **not** let the LLM issue SQL.

The LLM may suggest search terms only. Python performs parameterized searches through `FoodService._search_local_off()` or a dedicated wrapper.

For each parsed food:

1. Try exact/common local aliases first, e.g.:
   - `coke` → `coca cola`, `cola`
   - `donut` → `doughnut`, `glazed doughnut`, `ring doughnut`
2. Query local OFF table.
3. Keep top N candidates.
4. Prefer candidates with:
   - valid `carbs_per_100g`
   - valid `fat_per_100g`
   - plausible serving size
   - higher text similarity
   - fewer quality flags
5. Return selected match plus alternatives for transparency.

---

## Deterministic Nutrition Calculation

The code, not the model, calculates:

- per-item serving grams/ml
- carbs
- fat
- sugars
- calories
- total meal carbs/fat/sugar/calories

Example rules:

- `can` → 330 ml for soft drinks unless product serving says otherwise.
- `packet` → use OFF serving size if present; otherwise configured default for category.
- `slice` → use configured UK standard or product serving size.
- If no serving known, mark estimate as uncertain and use a conservative default.

The final response must include confidence/uncertainty when serving assumptions are used.

---

## Random Simulated User/Profile

For scenario mode, select a random anchor profile from the simulator profile set, e.g.:

- well controlled
- post-meal spike dominant
- fat delayed spike
- insulin sensitive
- brittle
- dawn phenomenon
- exercise sensitive

The selected profile affects:

- carb ratio
- insulin sensitivity
- fat-delay risk
- expected peak timing
- exercise/alcohol sensitivity if present

The response should say something like:

> "For this simulation I picked a Post-Meal Spike Dominant profile..."

This keeps it clear that the advice is scenario/simulator-based, not real patient-specific dosing guidance.

---

## Historical/Simulated Context

Search `food_history_90d.json` / `food_history_90d_enhanced.json` for similar meals.

Use this to add grounded context:

```text
A similar high-sugar meal in the simulated history showed a rapid rise within 45–60 minutes and a peak around 2 hours.
```

Where available, include:

- meal name
- carb estimate
- bolus taken
- peak delta
- peak time
- low/high outcome
- context modifiers: alcohol, walking, heat, exercise

---

## Final Companion Response Contract

The final response should contain:

1. **Profile selected**
2. **Foods identified**
3. **Database-backed nutrition evidence**
4. **Likely glucose timeline**
5. **Risk flags**
6. **Educational estimate only**
7. **What to monitor**
8. **Safety disclaimer**

Example structure:

```text
For this simulation I picked a Post-Meal Spike Dominant profile.

I found:
- 2 doughnuts: ~X g carbs, ~Y g fat
- 3 cans of cola: ~Z g carbs, mostly fast sugar

Total: ~N g carbs, ~M g fat.

Likely pattern:
- 15–30 min: cola starts raising glucose quickly
- 45–90 min: strong upward trend likely
- ~2 hours: likely near/after peak, depending on insulin timing
- 3–4 hours: doughnut fat may prolong or delay part of the rise

Educational estimate only: with this simulated profile's 1:R carb ratio, this meal corresponds to ~B units, but this is not a dosing instruction.
```

---

## Implementation Target

Prefer extending existing code instead of creating new ad-hoc scripts.

Likely implementation file:

```text
app/t1d_companion/local_loop.py
```

or refactor into existing:

```text
app/t1d_companion/fast_analysis.py
```

Suggested functions:

```python
async def parse_scenario_local_llm(text: str) -> ScenarioParse: ...

def pick_random_profile(seed: int | None = None) -> PatientConfig: ...

async def search_food_candidates(food: ParsedFood) -> list[FoodCandidate]: ...

def calculate_nutrition(parsed_foods, selected_candidates) -> MealNutrition: ...

def find_similar_meals(parsed_foods, profile) -> list[HistoricalMeal]: ...

async def generate_companion_response_local_llm(evidence_bundle) -> str: ...

async def run_local_companion_scenario(text: str, seed: int | None = None) -> CompanionResult: ...
```

---

## Important Safety Constraints

- Never say: "take X units".
- Say: "educational estimate suggests ~X units for this simulated profile".
- Numeric carb/fat/sugar values must be database/code-derived.
- Local LLM may only summarize or explain provided evidence.
- If database search confidence is low, say so.
- Alcohol + exercise must flag delayed hypo risk.
- High-fat meals must flag delayed spike risk.
- This is educational/simulator output, not medical advice.

---

## Bottom Line

We are not trying to make the model a nutrition database.

We are building a local AI companion loop where:

- LLM = language interface and explanation layer
- PostgreSQL/OpenFoodFacts/McCance/local tables = nutrition source of truth
- simulator profiles = personalization layer
- code = deterministic calculation and safety guardrail layer

This is the correct next step for the project.
