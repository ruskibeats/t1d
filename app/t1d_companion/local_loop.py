#!/usr/bin/env python3
"""All-local T1D companion scenario loop.

Pipeline:
1. Parse a natural-language meal scenario with local Ollama into structured food items.
2. Pick a random simulator anchor profile.
3. Search local PostgreSQL/OpenFoodFacts via FoodService.
4. Rank candidates and calculate nutrition deterministically.
5. Ask local Ollama to write a companion response using only the evidence bundle.

The local LLM is deliberately not the nutrition source of truth.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import random
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.core.database import db_manager, get_settings
from app.food.service import FoodService
from app.simulator.patient_factory import generate_patient_config, generate_profile_json
from app.simulator.schemas import AnchorType

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", os.getenv("OLLAMA_HOST", "http://192.168.0.211:11434"))
DEFAULT_OLLAMA_MODEL = os.getenv("T1D_LOCAL_MODEL", "llama3.1:latest")
PROMPTS_DIR = Path(__file__).with_name("prompts")
REFERENCE_CSV = Path("/root/t1d/hupaucm/carbs_and_cals_with_macros.csv")
LOCAL_FOOD_DB = Path("/root/t1d/data/t1d_food_database.json")

UNIT_TO_GRAMS_OR_ML = {
    "can": 330,
    "cans": 330,
    "packet": 25,
    "packets": 25,
    "bag": 25,
    "bags": 25,
    "slice": 30,
    "slices": 30,
    "roll": 60,
    "rolls": 60,
    "piece": 100,
    "pieces": 100,
    "portion": 100,
    "portions": 100,
    "pint": 568,
    "pints": 568,
    "pot": 200,
    "pots": 200,
    "wing": 50,
    "wings": 50,
    "ml": 1,
    "g": 1,
}

ALIASES = {
    "coke": ["coca cola", "coke", "cola"],
    "cola": ["coca cola", "cola", "coke"],
    "diet coke": ["diet coke", "coca cola zero", "diet cola"],
    "donut": ["donut", "doughnut", "glazed doughnut", "ring doughnut"],
    "donuts": ["donut", "doughnut", "glazed doughnut", "ring doughnut"],
    "doughnut": ["doughnut", "donut", "glazed doughnut", "ring doughnut"],
    "crisps": ["crisps", "potato crisps", "ready salted crisps"],
    "chips": ["chips", "french fries", "fries"],
    "fries": ["fries", "french fries", "chips"],
    "white bread": ["white bread", "sliced white bread"],
    "toast": ["white bread", "toast", "sliced bread"],
    "pizza": ["pepperoni pizza", "pizza", "pizza pepperoni"],
    "pepperoni pizza": ["pepperoni pizza", "pizza", "pizza pepperoni"],
    "lager": ["lager", "beer", "pilsner"],
    "beer": ["beer", "lager", "pilsner"],
    "ice cream": ["ice cream", "vanilla ice cream", "dairy ice cream", "chocolate ice cream"],
    "chicken wings": ["chicken wings", "breaded chicken", "chicken wing", "buffalo wings"],
    "coleslaw": ["coleslaw", "slaw", "cabbage slaw"],
}


@dataclass
class ParsedFood:
    item: str
    quantity: float = 1.0
    unit: str | None = None
    search_terms: list[str] = field(default_factory=list)


@dataclass
class SelectedFoodEvidence:
    parsed: dict[str, Any]
    selected_match: dict[str, Any] | None
    alternatives: list[dict[str, Any]]
    assumed_serving_g_or_ml: float | None
    computed: dict[str, float] | None
    confidence: str
    carb_range_g: tuple[float, float] = (0.0, 0.0)  # (min_g, max_g) over plausible candidates
    warnings: list[str] = field(default_factory=list)
    comparison_summary: dict[str, Any] = field(default_factory=dict)


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _load_prompt(name: str, fallback: str) -> str:
    path = PROMPTS_DIR / name
    try:
        text = path.read_text().strip()
        return text or fallback
    except FileNotFoundError:
        return fallback


def _extract_json(text: str) -> Any:
    """Extract the first JSON object/array from a sometimes-chatty model response."""
    text = text.strip()
    blocks = _JSON_BLOCK_RE.findall(text)
    candidates = blocks + [text]
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        start_positions = [p for p in [candidate.find("{"), candidate.find("[")] if p >= 0]
        if not start_positions:
            continue
        start = min(start_positions)
        for end in range(len(candidate), start, -1):
            fragment = candidate[start:end].strip()
            try:
                return json.loads(fragment)
            except json.JSONDecodeError:
                continue
    raise ValueError("No valid JSON found in local LLM response")


def _canonical_item(value: str) -> str:
    item = value.strip().lower()
    if item.endswith("oes"):
        singular = item[:-2]  # potatoes/tomatoes -> potato/tomato
    elif item.endswith("ies"):
        singular = item[:-3] + "y"
    else:
        singular = item.rstrip("s")
    if singular in {"donut", "doughnut"}:
        return "donut"
    if item in {"coca cola", "coca-cola", "coke", "cola"}:
        return "coke"
    if item in {"diet coke", "diet cola"}:
        return "diet coke"
    if item in {"crisps", "chips"}:
        return item
    return singular


def _normalise_food_dict(raw: dict[str, Any]) -> ParsedFood:
    item = _canonical_item(str(raw.get("item") or raw.get("name") or raw.get("food") or "unknown food"))
    quantity = raw.get("quantity", raw.get("qty", 1))
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        quantity = 1.0
    unit = raw.get("unit")
    unit = str(unit).strip().lower() if unit else None
    terms = raw.get("search_terms") or raw.get("search") or []
    if isinstance(terms, str):
        terms = [terms]
    terms = [str(term).strip().lower() for term in terms if str(term).strip()]
    if not terms:
        terms = ALIASES.get(item, [item])
    return ParsedFood(item=item, quantity=quantity, unit=unit, search_terms=terms)


def fallback_parse_scenario(text: str) -> list[ParsedFood]:
    """Deterministic fallback for common quantity/unit food phrases."""
    lower = text.lower()
    foods: list[ParsedFood] = []

    patterns = [
        (r"(\d+(?:\.\d+)?)\s+(?:cans?\s+of\s+)?(diet\s+coke|coke|cola)\b", "can"),
        (r"(\d+(?:\.\d+)?)\s+(donuts?|doughnuts?)\b", None),
        (r"(\d+(?:\.\d+)?)\s+(?:packets?|bags?)\s+of\s+(crisps|chips)\b", "packet"),
        (r"(\d+(?:\.\d+)?)\s+(slices?)\s+of\s+(pepperoni pizza|pizza|toast|white bread|bread)\b", "slice"),
        (r"(\d+(?:\.\d+)?)\s+(pints?)\s+of\s+(lager|beer)\b", "pint"),
    ]
    for pattern, forced_unit in patterns:
        for match in re.finditer(pattern, lower):
            qty = float(match.group(1))
            if len(match.groups()) >= 3 and match.group(3):
                unit = forced_unit or match.group(2)
                item = match.group(3)
            else:
                unit = forced_unit
                item = match.group(2)
            item = item.rstrip("s") if item not in {"crisps", "chips"} else item
            item = _canonical_item(item)
            foods.append(ParsedFood(item=item, quantity=qty, unit=unit, search_terms=ALIASES.get(item, [item])))

    # Handle "a packet of crisps", "a donut", etc.
    if re.search(r"\ba\s+(?:packet|bag)\s+of\s+crisps\b", lower) and not any(f.item == "crisps" for f in foods):
        foods.append(ParsedFood(item="crisps", quantity=1, unit="packet", search_terms=ALIASES["crisps"]))
    if re.search(r"\ba\s+donut\b", lower) and not any("donut" in f.item for f in foods):
        foods.append(ParsedFood(item="donut", quantity=1, search_terms=ALIASES["donut"]))

    if not foods:
        # Last resort: split on "and" / "with" / commas
        cleaned = text.strip().lower()
        # Remove em dashes and other punctuation
        cleaned = cleaned.replace(chr(0x2014), " ").replace(chr(0x2013), " ").replace("-", " ")
        # Remove trailing question
        qpos = cleaned.rfind("?")
        if qpos >= 0:
            cleaned = cleaned[:qpos]
        # Aggressive stripping: keep only the food request part
        # Find where food/meal/drink description starts after context
        # Common trigger phrases: "want ", "have ", "eat ", "get ", "order "
        for trigger in [" want ", " have ", " eat ", " get ", " order "]:
            idx = cleaned.find(trigger)
            if idx >= 0:
                cleaned = cleaned[idx + len(trigger):]
                break
        # Remove articles and leading "to eat" style prefixes
        for ctx in ["a standard ", "a large ", "a small ", "a ", "an ", "the ", "some ", "to eat ", "eat "]:
            if cleaned.startswith(ctx):
                cleaned = cleaned[len(ctx):]
                break
        cleaned = cleaned.strip().strip(" ,-()?!")
        # Remove trailing question context like "what will likely happen"
        for trailing in ["what will likely happen", "what will happen", "what happens", "what would happen"]:
            wtf = cleaned.rfind(trailing)
            if wtf >= 0:
                cleaned = cleaned[:wtf].strip()
        # Strip remaining leftover context after food description
        # e.g. "2pm" at start
        if re.match(r"^\d+\s*(?:pm|am|pm|am|:)\s*,", cleaned):
            cleaned = re.sub(r"^\d+\s*(?:pm|am|pm|am|:)\s*,\s*", "", cleaned)
        # Split on " and " / " with " / "," — recursively
        # First pass: split on primary separator " and "
        for sep in [" and ", ","]:
            parts = cleaned.split(sep)
            if len(parts) >= 2:
                foods = []
                for p in parts:
                    p = p.strip(" ,-()")
                    if not p:
                        continue
                    # Second pass: split each part on " with "
                    sub_parts = p.split(" with ")
                    for sp in sub_parts:
                        sp = sp.strip()
                        if not sp:
                            continue
                        # Try "2 scoops of ice cream" pattern
                        m = re.match(r"(\d+(?:\.\d+)?)\s+(\w+)\s+of\s+(.+)", sp)
                        if m:
                            foods.append(ParsedFood(item=m.group(3), quantity=float(m.group(1)), unit=m.group(2), search_terms=[m.group(3)]))
                        else:
                            # Try "two scoops of ice cream" (word numbers)
                            WORD_NUM = {"a":1, "one":1, "two":2, "three":3, "four":4, "five":5, "six":6}
                            m = re.match(r"(one|two|three|four|five|six|\d+)\s+(\w+)\s+of\s+(.+)", sp)
                            if m:
                                qty = WORD_NUM.get(m.group(1), float(m.group(1)) if m.group(1).isdigit() else 1)
                                foods.append(ParsedFood(item=m.group(3), quantity=qty, unit=m.group(2), search_terms=[m.group(3)]))
                            else:
                                # Try "plate pasta" or "plate of pasta"
                                m = re.match(r"(?:a|an|the|two|\d+)?\s*(\w+)\s+(?:of\s+)?(.+)", sp)
                                if m:
                                    unit = m.group(1).strip("s")
                                    if unit in {"plate", "bowl", "cup", "scoop", "can", "pint", "piece", "slice", "glass", "bottle", "serving", "wing", "wings", "pot", "pots"}:
                                        foods.append(ParsedFood(item=m.group(2), quantity=1, unit=unit, search_terms=[m.group(2)]))
                                    else:
                                        foods.append(ParsedFood(item=sp, quantity=1, search_terms=[sp]))
                                else:
                                    foods.append(ParsedFood(item=sp, quantity=1, search_terms=[sp]))
                if foods:
                    break
        else:
            # No multi-part split worked; try single " with " split
            parts = cleaned.split(" with ")
            if len(parts) >= 2:
                foods = []
                for p in parts:
                    p = p.strip()
                    if not p: continue
                    m = re.match(r"(?:a|an|the|two|\d+)?\s*(\w+)\s+(?:of\s+)?(.+)", p)
                    if m and m.group(1).strip("s") in {"plate", "bowl", "cup", "scoop", "can", "pint", "piece", "slice", "glass", "bottle", "serving", "wing", "wings", "pot", "pots"}:
                        foods.append(ParsedFood(item=m.group(2), quantity=1, unit=m.group(1).strip("s"), search_terms=[m.group(2)]))
                    else:
                        foods.append(ParsedFood(item=p, quantity=1, search_terms=[p]))

    if not foods:
        foods = [ParsedFood(item=text.strip().lower(), quantity=1, search_terms=[text.strip().lower()])]

    return foods


def _safe_num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_local_food_db() -> dict[str, Any]:
    if not LOCAL_FOOD_DB.exists():
        return {}
    try:
        return json.loads(LOCAL_FOOD_DB.read_text()).get("foods", {})
    except Exception:
        return {}


def find_reference_rows(food: ParsedFood, limit: int = 5) -> list[dict[str, Any]]:
    """Find local deterministic reference rows for comparison reasoning."""
    rows: list[dict[str, Any]] = []
    terms = {food.item.lower(), food.item.lower().rstrip("s"), *[t.lower() for t in food.search_terms]}
    # Avoid false positives from tiny terms such as "ale" matching "kale".
    terms = {term for term in terms if term and len(term) >= 4}

    for name, values in _load_local_food_db().items():
        name_l = name.lower()
        if any(re.search(rf"\\b{re.escape(term)}\\b", name_l) or name_l == term for term in terms):
            rows.append({
                "source": "t1d_food_database",
                "name": name,
                "carbs_100g": values.get("carbs"),
                "fat_100g": values.get("fat"),
                "protein_100g": values.get("protein"),
            })

    if REFERENCE_CSV.exists():
        try:
            with REFERENCE_CSV.open(newline="") as handle:
                for row in csv.DictReader(handle):
                    haystack = f"{row.get('Food') or ''} {row.get('Validation Match') or ''}".lower()
                    if any(re.search(rf"\\b{re.escape(term)}\\b", haystack) for term in terms):
                        rows.append({
                            "source": "carbs_and_cals_mccance",
                            "name": row.get("Food"),
                            "validation_match": row.get("Validation Match"),
                            "carbs_100g": _safe_num(row.get("Carbs g / 100g")),
                            "fat_100g": _safe_num(row.get("Fat g / 100g")),
                            "protein_100g": _safe_num(row.get("Protein g / 100g")),
                            "confidence": row.get("Confidence"),
                        })
        except Exception:
            pass
    return rows[:limit]


async def parse_scenario_local_llm(
    text: str,
    *,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> tuple[list[ParsedFood], str | None]:
    """Parse scenario with local Ollama, falling back to regex if needed."""
    system = _load_prompt(
        "parser_system.txt",
        (
            "Return ONLY valid JSON. Parse the user's T1D meal scenario into this exact shape: "
            '{"foods":[{"item":"lowercase food","quantity":number,"unit":string_or_null,'
            '"search_terms":["term1","term2"]}],"question":"short user question"}. '
            "Do not include nutrition values. Do not explain."
        ),
    )
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            response = await client.post(
                f"{ollama_url.rstrip('/')}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0,
                    "max_tokens": 300,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = _extract_json(content)
            foods_raw = data.get("foods", data if isinstance(data, list) else [])
            foods = [_normalise_food_dict(item) for item in foods_raw if isinstance(item, dict)]
            if foods:
                # Merge deterministic regex hints back into LLM parse. Local models
                # often identify "coke" but drop "can" from "3 cans of coke".
                fallback_foods = fallback_parse_scenario(text)
                by_item = {food.item: food for food in fallback_foods}
                for food in foods:
                    hint = by_item.get(food.item)
                    if hint:
                        if not food.unit and hint.unit:
                            food.unit = hint.unit
                        if not food.search_terms and hint.search_terms:
                            food.search_terms = hint.search_terms
                return foods, content
        except Exception as exc:
            raw = f"local_llm_parse_failed: {exc}"
            return fallback_parse_scenario(text), raw
    return fallback_parse_scenario(text), None


def pick_random_profile(seed: int | None = None) -> tuple[Any, dict[str, Any]]:
    rng = random.Random(seed)
    anchor = rng.choice(list(AnchorType))
    profile_seed = rng.randint(1, 1_000_000)
    config = generate_patient_config(anchor, profile_seed)
    return config, generate_profile_json(config)


def pick_profile_by_anchor(anchor_type: str | AnchorType, seed: int = 42) -> tuple[Any, dict[str, Any]]:
    if isinstance(anchor_type, str):
        anchor_type = AnchorType(anchor_type)
    config = generate_patient_config(anchor_type, seed)
    return config, generate_profile_json(config)


def _is_diet_or_zero(candidate: dict[str, Any]) -> bool:
    text = f"{candidate.get('name') or ''} {candidate.get('brand') or ''}".lower()
    return any(token in text for token in ["diet", "zero", "sugar free", "no sugar", "light"])


def _candidate_score(food: ParsedFood, candidate: dict[str, Any],
                     medians: dict[str, float] | None = None) -> float:
    """Score a candidate food item for relevance.

    Returns a score where higher is better. Typical range is roughly [-0.2, 1.0].
    Score components:
    - name_sim: 0-1 from lexical name matching
    - sem_sim: 0-1 from embedding similarity (if available)
    - quality: 0-1 from data completeness, consistency, and typicality
    Weights: 0.40 name + 0.35 semantic + 0.25 quality
    """
    name = str(candidate.get("name") or "").lower()
    item = food.item.lower()

    # 1. Name similarity (0-1)
    # Prefer names where the item is the primary (first) word.
    # e.g. 'beer' -> 'Beer' (1.0) > 'Lager Beer' (0.8) > 'Root Beer' (0.5)
    # This prevents 'Root Beer' or 'Cake Donut' from outscoring actual beer/donut.
    import re
    esc = re.escape(item)
    has_word = bool(re.search(r'\b' + esc + r'\b', name, re.IGNORECASE))
    
    if not has_word:
        term_hits = sum(1 for t in food.search_terms if t and t in name)
        name_sim = min(term_hits * 0.3, 0.5)
    elif name == item:
        name_sim = 1.0
    elif re.match(r'\b' + esc, name, re.IGNORECASE):
        # Item is the first word (word boundary at start)
        name_sim = 1.0
    elif re.search(esc + r'\b', name, re.IGNORECASE):
        # Item is the last word (word boundary at end): 'Lager Beer'
        name_sim = 0.8
    else:
        # Item is mid-name: 'Root Beer', 'Cake Donut'
        name_sim = 0.5
    
    # Small brand bonus
    brand_val = str(candidate.get("brand") or "").lower()
    if brand_val and brand_val not in ("none", "", "null"):
        name_sim = min(name_sim + 0.05, 1.0)

    # 2. Semantic similarity (0-1, from pgvector embedding search)
    sem_sim = float(candidate.get("_semantic_similarity") or 0.0)

    # 3. Data quality score (0-1, food-agnostic)
    quality = _data_quality_score(candidate, medians)

    # 4. Combine with fixed weights
    score = 0.40 * name_sim + 0.35 * sem_sim + 0.25 * quality

    return score


# Cache of per-product-name median macros, populated lazily
_name_medians: dict[str, dict[str, float]] = {}


async def _get_name_medians(session, product_name: str) -> dict[str, float] | None:
    """Compute median macros from the DB for all products matching a name.
    Cached per name string. Returns None if no data."""
    from sqlalchemy import text
    name_key = product_name.lower()
    if name_key in _name_medians:
        return _name_medians[name_key]
    result = await session.execute(text('''
        SELECT
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY carbs_100g) as median_carbs,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fat_100g) as median_fat,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY proteins_100g) as median_protein,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY energy_kcal_100g) as median_calories,
            COUNT(*) as cnt
        FROM openfoodfacts_products
        WHERE LOWER(product_name) = :name
          AND carbs_100g IS NOT NULL
    '''), {'name': name_key})
    row = result.fetchone()
    if row and row[4] >= 3:  # need at least 3 products for a meaningful median
        medians = {
            'carbs': float(row[0]) if row[0] else None,
            'fat': float(row[1]) if row[1] else None,
            'protein': float(row[2]) if row[2] else None,
            'calories': float(row[3]) if row[3] else None,
            'count': row[4],
        }
        _name_medians[name_key] = medians
        return medians
    return None


def _data_quality_score(c: dict, medians: dict[str, float] | None = None) -> float:
    """Score a product entry by data completeness, self-consistency, and typicality.

    This is food-agnostic: it rewards entries that have a brand, serving size,
    and complete nutrition data, and penalizes entries with inconsistent or
    suspicious values. When medians are provided, it also rewards values close
    to the database median for that product name (preferring typical over outlier).
    Returns a float in [0, 1].
    """
    quality = 0.0

    # Identity / metadata
    brand = c.get("brand")
    if brand and str(brand).lower() not in ("none", "", "null"):
        quality += 0.15
    if c.get("serving_size"):
        quality += 0.10

    # Nutrition completeness: core macros
    macros_present = 0
    for key in ("carbs_per_100g", "protein_per_100g", "fat_per_100g", "calories_per_100g"):
        if c.get(key) is not None:
            macros_present += 1
    quality += 0.05 * macros_present  # up to +0.20

    # Extra fields (weaker signal)
    for key in ("sugars_per_100g", "fiber_per_100g", "sodium_per_100g"):
        if c.get(key) is not None:
            quality += 0.02  # up to +0.06

    # Consistency: estimated calories from macros should match stated calories
    carbs = c.get("carbs_per_100g")
    protein = c.get("proteins_100g")
    fat = c.get("fat_per_100g")
    calories = c.get("calories_per_100g")
    if calories is not None and carbs is not None and protein is not None and fat is not None:
        estimated = carbs * 4 + protein * 4 + fat * 9
        if estimated > 0:
            ratio = calories / estimated
            if 0.7 <= ratio <= 1.3:
                quality += 0.10  # consistent
            elif 0.5 <= ratio <= 1.5:
                pass            # roughly OK
            else:
                quality -= 0.15  # inconsistent — likely bad data

    # Typicality: prefer values close to the database median for this product name
    # This is generic — no food-specific knowledge, just "prefer the middle of the pack"
    if medians:
        typicality = 0.0
        # Map median keys to candidate dict keys (OFF uses plural column names)
        field_map = {
            'carbs': 'carbs_per_100g',
            'fat': 'fat_per_100g',
            'protein': 'proteins_100g',
            'calories': 'calories_per_100g',
        }
        for key, median_val in [('carbs', medians.get('carbs')), ('fat', medians.get('fat')),
                                 ('protein', medians.get('protein')), ('calories', medians.get('calories'))]:
            if median_val is None:
                continue
            val = c.get(field_map[key])
            if val is None or median_val <= 0:
                continue
            ratio = val / median_val
            if 0.5 <= ratio <= 2.0:
                typicality += 0.03  # within 2x of median
            elif 0.25 <= ratio <= 4.0:
                typicality += 0.01  # within 4x — acceptable
            else:
                typicality -= 0.05  # far from median — likely an outlier/variant
        quality += max(typicality, -0.15)  # cap the penalty

    # Penalty for clearly broken values
    if (calories is not None and calories < 0) or (carbs is not None and carbs < 0):
        quality -= 0.30

    # Penalty for near-empty entries (carbs-only placeholders)
    if carbs is not None and fat is None and protein is None and calories is None:
        quality -= 0.10

    return max(0.0, min(1.0, quality))


def _public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "name",
        "brand",
        "barcode",
        "carbs_per_100g",
        "sugars_per_100g",
        "fat_per_100g",
        "protein_per_100g",
        "calories_per_100g",
        "serving_size",
    ]
    return {key: candidate.get(key) for key in keys}


async def search_food_candidates(service: FoodService, food: ParsedFood, limit_per_term: int = 5) -> list[dict[str, Any]]:
    """Search for food candidates using the FoodSearch facade.

    Merges semantic and lexical results, keyed by barcode for deduplication.
    Semantic similarity is preserved in _semantic_similarity field.
    """
    from app.food.search import FoodSearch

    facade = FoodSearch(service)
    candidates = await facade.search(food, limit=limit_per_term)

    # Compute per-name medians for typicality scoring
    medians = await _get_name_medians(service.db, food.item)
    candidates.sort(key=lambda c: _candidate_score(food, c, medians), reverse=True)
    return candidates


def build_comparison_summary(food: ParsedFood, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    plausible = [c for c in candidates[:10] if c.get("carbs_per_100g") is not None]
    carbs_values = [float(c["carbs_per_100g"]) for c in plausible]
    fat_values = [float(c.get("fat_per_100g") or 0) for c in plausible]
    refs = find_reference_rows(food)
    ref_carbs = [r.get("carbs_100g") for r in refs if r.get("carbs_100g") is not None]
    ambiguities = []
    item = food.item.lower()
    if item in {"pizza", "pepperoni pizza"}:
        ambiguities.append("Pizza slice size varies a lot: thin crust vs deep pan vs takeaway slice.")
    if item in {"lager", "beer"}:
        ambiguities.append("Alcohol can increase delayed hypo risk even when carb grams look modest.")
    if carbs_values and max(carbs_values) - min(carbs_values) > 15:
        ambiguities.append("OpenFoodFacts candidates vary widely; serving/product choice materially changes estimate.")
    return {
        "off_candidate_count": len(plausible),
        "off_carbs_100g_range": [round(min(carbs_values), 1), round(max(carbs_values), 1)] if carbs_values else None,
        "off_fat_100g_range": [round(min(fat_values), 1), round(max(fat_values), 1)] if fat_values else None,
        "reference_rows": refs,
        "reference_carbs_100g_range": [round(min(ref_carbs), 1), round(max(ref_carbs), 1)] if ref_carbs else None,
        "ambiguities": ambiguities,
    }


def _parse_grams_from_serving(serving_size: Any) -> float | None:
    if not serving_size:
        return None
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*g\b", str(serving_size).lower())
    if matches:
        return float(matches[-1])
    ml_matches = re.findall(r"(\d+(?:\.\d+)?)\s*ml\b", str(serving_size).lower())
    if ml_matches:
        return float(ml_matches[-1])
    return None


def serving_amount(food: ParsedFood, candidate: dict[str, Any] | None) -> tuple[float, list[str]]:
    warnings: list[str] = []
    qty = float(food.quantity or 1)
    unit = (food.unit or "").lower()
    item = food.item.lower()

    # Food-specific unit overrides before generic units.
    if item in {"pizza", "pepperoni pizza"} and unit in {"slice", "slices"}:
        warnings.append("Assumed 100g per pizza slice; slice size varies by crust/takeaway.")
        return qty * 100, warnings
    if item in {"lager", "beer"} and unit in {"pint", "pints"}:
        return qty * 568, warnings

    if unit in UNIT_TO_GRAMS_OR_ML:
        return qty * UNIT_TO_GRAMS_OR_ML[unit], warnings

    if candidate:
        serving = _parse_grams_from_serving(candidate.get("serving_size"))
        if serving:
            return qty * serving, warnings

    if item in {"donut", "donuts", "doughnut", "doughnuts"}:
        warnings.append("No serving size selected; assumed 70g per doughnut.")
        return qty * 70, warnings
    if item in {"coke", "cola", "diet coke", "diet cola"}:
        warnings.append("No unit supplied; assumed 330ml can.")
        return qty * 330, warnings
    if item in {"crisps", "chips"}:
        warnings.append("No unit supplied; assumed 25g packet.")
        return qty * 25, warnings
    if item in {"pizza", "pepperoni pizza"}:
        warnings.append("Assumed 100g per pizza slice unless a product serving size is selected.")
        return qty * 100, warnings
    if item in {"lager", "beer"}:
        warnings.append("Assumed UK pint = 568ml.")
        return qty * 568, warnings

    warnings.append("No serving size found; assumed 100g per item/portion.")
    return qty * 100, warnings


def _carb_range_for_candidates(
    food: ParsedFood,
    candidates: list[dict[str, Any]],
    max_alternatives: int = 5,
    min_score_fraction: float = 0.7,
) -> tuple[float, float]:
    """Compute a plausible carb range (min_g, max_g) for a food from its candidates.

    Selects the top N candidates whose score is within `min_score_fraction` of
    the best score, converts each candidate's carbs_per_100g to grams using
    the same serving logic as the point estimate, and returns (min, max).

    Returns (0.0, 0.0) when no candidates have carb data.
    """
    if not candidates:
        return (0.0, 0.0)

    # Score candidates that have carb data
    scored = [
        (c, _candidate_score(food, c))
        for c in candidates
        if c.get("carbs_per_100g") is not None
    ]
    if not scored:
        return (0.0, 0.0)

    scored.sort(key=lambda x: x[1], reverse=True)
    best_score = scored[0][1]
    threshold = best_score * min_score_fraction

    plausible = [
        c for (c, s) in scored[:max_alternatives]
        if s >= threshold
    ] or [scored[0][0]]

    # Compute carbs in grams for each plausible candidate using same serving
    # logic as the point estimate. Reuse serving_amount() for each candidate.
    carb_g_values = []
    for c in plausible:
        amount, _ = serving_amount(food, c)
        carbs_100g = c.get("carbs_per_100g") or 0
        carb_g_values.append(round(carbs_100g * amount / 100, 1))

    return (min(carb_g_values), max(carb_g_values))


def calculate_food_evidence(food: ParsedFood, candidates: list[dict[str, Any]]) -> SelectedFoodEvidence:
    selected = candidates[0] if candidates else None
    alternatives = [_public_candidate(c) for c in candidates[1:4]]
    if not selected:
        return SelectedFoodEvidence(
            parsed=asdict(food),
            selected_match=None,
            alternatives=[],
            assumed_serving_g_or_ml=None,
            computed=None,
            confidence="none",
            warnings=["No local database match found."],
            comparison_summary=build_comparison_summary(food, candidates),
        )

    amount, warnings = serving_amount(food, selected)
    carbs_100g = selected.get("carbs_per_100g") or 0
    fat_100g = selected.get("fat_per_100g") or 0
    sugars_100g = selected.get("sugars_per_100g") or 0
    protein_100g = selected.get("protein_per_100g") or 0
    kcal_100g = selected.get("calories_per_100g") or 0
    computed = {
        "carbs_g": round(carbs_100g * amount / 100, 1),
        "fat_g": round(fat_100g * amount / 100, 1),
        "sugars_g": round(sugars_100g * amount / 100, 1),
        "protein_g": round(protein_100g * amount / 100, 1),
        "kcal": round(kcal_100g * amount / 100, 0),
    }
    score = _candidate_score(food, selected)
    confidence = "high" if score >= 0.5 and not warnings else "medium" if score >= 0.2 else "low"
    carb_range_g = _carb_range_for_candidates(food, candidates)
    return SelectedFoodEvidence(
        parsed=asdict(food),
        selected_match=_public_candidate(selected),
        alternatives=alternatives,
        assumed_serving_g_or_ml=round(amount, 1),
        computed=computed,
        confidence=confidence,
        carb_range_g=carb_range_g,
        warnings=warnings,
        comparison_summary=build_comparison_summary(food, candidates),
    )


def find_similar_meals(foods: list[ParsedFood], limit: int = 3) -> list[dict[str, Any]]:
    """Find similar meals using the canonical historical meal matcher.
    
    Deprecated: Use app.services.historical_meal_matcher.summarize_similar_meals directly.
    Kept for compatibility with legacy callers.
    """
    from app.services.historical_meal_matcher import find_similar_meals as matcher_find_similar
    
    # Get matches directly with the limit
    matches = matcher_find_similar(
        food_name=foods[0].item if foods else None,
        max_matches=limit,
    )
    
    # Return as list of dicts for evidence bundle serialization
    return [asdict(m) for m in matches]


async def generate_companion_response(
    evidence_bundle: dict[str, Any],
    *,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> str:
    system = "\n\n".join(
        [
            _load_prompt(
                "companion_system.txt",
                (
                    "You are a warm, practical T1D companion in simulator mode. Use ONLY the JSON evidence provided. "
                    "Do not invent nutrition numbers, caffeine effects, or extra foods. "
                    "Never say 'take X units'; say 'educational estimate for this simulated profile'. "
                    "You MUST mention the selected profile, meal totals, educational bolus estimate, risk flags, "
                    "monitoring timing, and uncertainty. Sound human and useful, not robotic."
                ),
            ),
            _load_prompt("safety_rules.txt", "Educational simulator output only; do not provide dosing instructions."),
        ]
    )
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{ollama_url.rstrip('/')}/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(evidence_bundle, indent=2)},
                ],
                "temperature": 0.45,
                "max_tokens": 750,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


async def run_local_companion_scenario(
    text: str,
    *,
    seed: int | None = None,
    anchor: str | None = None,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> dict[str, Any]:
    foods, raw_parse = await parse_scenario_local_llm(text, ollama_url=ollama_url, model=model)
    if anchor:
        config, profile_json = pick_profile_by_anchor(anchor)
    else:
        config, profile_json = pick_random_profile(seed)

    settings = get_settings()
    db_manager.init_db(settings.database_url)

    evidence_items: list[SelectedFoodEvidence] = []
    async with db_manager.get_session() as session:
        service = FoodService(session)
        for food in foods:
            candidates = await search_food_candidates(service, food)
            evidence_items.append(calculate_food_evidence(food, candidates))

    totals = {"carbs_g": 0.0, "fat_g": 0.0, "sugars_g": 0.0, "protein_g": 0.0, "kcal": 0.0}
    for item in evidence_items:
        if not item.computed:
            continue
        for key in totals:
            totals[key] += item.computed.get(key, 0.0)
    totals = {key: round(value, 1) for key, value in totals.items()}

    # Load enriched insights for the selected anchor
    from app.simulator.schemas import AnchorType
    enriched_path = Path("/root/t1d/sim_user_insights/outputs/sim_users_enriched.json")
    enriched_anchor_data = None
    if enriched_path.exists():
        try:
            enriched_all = json.loads(enriched_path.read_text())
            for ea in enriched_all.get("anchors", []):
                if ea.get("anchor_type") == config.anchor_type.value:
                    enriched_anchor_data = ea
                    break
        except Exception:
            pass

    similar_meals = find_similar_meals(foods)
    bolus_estimate = round(totals["carbs_g"] / config.carb_ratio, 1) if config.carb_ratio else None
    risk_flags = []
    if totals["carbs_g"] >= 80:
        risk_flags.append("large_carb_load")
    if totals["sugars_g"] >= 50:
        risk_flags.append("rapid_sugar_spike")
    if totals["fat_g"] >= 15:
        risk_flags.append("fat_may_extend_or_delay_rise")
    if any(food.item.lower() in {"lager", "beer"} for food in foods):
        risk_flags.append("alcohol_can_increase_delayed_hypo_risk")
    if config.exercise_drop_factor >= 3:
        risk_flags.append("exercise_sensitive_profile_watch_later_lows_if_active")

    evidence_bundle = {
        "scenario": text,
        "selected_sim_profile": {
            "anchor_type": config.anchor_type.value,
            "label": profile_json.get("anchor_label"),
            "description": profile_json.get("description"),
            "carb_ratio": config.carb_ratio,
            "insulin_sensitivity": config.insulin_sensitivity,
            "meal_rise_factor": config.meal_rise_factor,
            "fat_delay_hours": config.fat_delay_hours,
            "exercise_drop_factor": config.exercise_drop_factor,
            "hypo_risk": config.hypo_risk,
            "seed": config.seed,
        },
        "parsed_foods": [asdict(food) for food in foods],
        "raw_llm_parse_response": raw_parse,
        "database_matches_and_calculations": [asdict(item) for item in evidence_items],
        "meal_totals": totals,
        "educational_bolus_estimate_units": bolus_estimate,
        "risk_flags": risk_flags,
        "timing_rules": [
            "Fast sugars can start raising glucose in ~15-30 minutes.",
            "A large carb load is often prominent by ~60-120 minutes.",
            "If fat is >=15g, part of the rise may extend or delay over ~2-4+ hours.",
        ],
        "similar_historical_or_simulated_meals": similar_meals,
        "profile_insights": enriched_anchor_data,
    }
    response = await generate_companion_response(evidence_bundle, ollama_url=ollama_url, model=model)
    return {"evidence": evidence_bundle, "response": response}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the all-local T1D companion scenario loop.")
    parser.add_argument("scenario", help="Natural-language scenario question")
    parser.add_argument("--seed", type=int, help="Optional deterministic seed for random sim profile")
    parser.add_argument("--anchor", type=str, help="Specific anchor type: well_controlled, high_fat_delayed, etc.")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL)
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    args = parser.parse_args()

    result = asyncio.run(
        run_local_companion_scenario(
            args.scenario,
            seed=args.seed,
            anchor=args.anchor,
            ollama_url=args.ollama_url,
            model=args.model,
        )
    )
    if args.json:
        print(json.dumps(result, indent=2))
        return

    evidence = result["evidence"]
    profile = evidence["selected_sim_profile"]
    print("=" * 72)
    print("LOCAL T1D COMPANION")
    print("=" * 72)
    print(f"Scenario: {evidence['scenario']}")
    print(f"Profile: {profile['label']} ({profile['anchor_type']})")
    print("\nFoods / DB evidence:")
    for item in evidence["database_matches_and_calculations"]:
        parsed = item["parsed"]
        match = item["selected_match"]
        computed = item["computed"]
        print(f"- {parsed['quantity']} {parsed.get('unit') or ''} {parsed['item']}: confidence={item['confidence']}")
        if match and computed:
            print(f"  match: {match.get('name')} [{match.get('brand') or 'unknown brand'}]")
            print(f"  computed: {computed['carbs_g']}g carbs, {computed['fat_g']}g fat, {computed['sugars_g']}g sugars")
        else:
            print("  no DB match")
        for warning in item.get("warnings") or []:
            print(f"  warning: {warning}")
    totals = evidence["meal_totals"]
    print(f"\nTotals: {totals['carbs_g']}g carbs, {totals['fat_g']}g fat, {totals['sugars_g']}g sugars, {totals['kcal']} kcal")
    print(f"Educational bolus estimate for simulated profile: {evidence['educational_bolus_estimate_units']} units")
    print("\nCompanion response:\n")
    print(result["response"])


if __name__ == "__main__":
    main()
