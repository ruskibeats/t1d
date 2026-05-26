#!/usr/bin/env python3
"""
T1D Companion Fast Meal Analysis - with quantity/unit parsing.
"""
import sys
import asyncio
import json
import re
import os
import random
from pathlib import Path
from typing import Any

# Load .env file if it exists
_env_path = Path("/root/t1d/.env")
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

PROFILE_CONFIGS_PATH = Path("/root/t1d/data/profile_configs.json")
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL") or os.getenv("OLLAMA_HOST") or "http://192.168.0.211:11434"
DEFAULT_LOCAL_MODEL = os.getenv("T1D_LOCAL_MODEL", "llama3.1:latest")

# Serving sizes by unit (grams)
UNIT_TO_GRAMS = {
    "slice": 30, "slices": 30,
    "rasher": 30, "rashers": 30,
    "piece": 100, "pieces": 100,
    "roll": 60, "rolls": 60,
    "cup": 240, "cups": 240,
    "tbsp": 15, "tablespoon": 15, "tablespoons": 15,
    "can": 330, "cans": 330,
    "pint": 568, "pints": 568,
}

# Load profile configs
if PROFILE_CONFIGS_PATH.exists():
    with open(PROFILE_CONFIGS_PATH) as f:
        PROFILE_CONFIGS = json.load(f)
else:
    from app.simulator.patient_factory import generate_patient_config, generate_profile_json
    from app.simulator.schemas import AnchorType
    PROFILE_CONFIGS = {}
    for anchor in AnchorType:
        config = generate_patient_config(anchor, seed=42)
        profile = generate_profile_json(config)
        PROFILE_CONFIGS[anchor.value] = {"carb_ratio": round(config.carb_ratio, 1), "profile": profile}
    PROFILE_CONFIGS_PATH.parent.mkdir(exist_ok=True)
    with open(PROFILE_CONFIGS_PATH, 'w') as f:
        json.dump(PROFILE_CONFIGS, f, indent=2)

def parse_quantity_unit(text: str) -> tuple:
    """
    Parse '3 slices of bread' → (3, 'slice', 'bread').
    Returns (quantity, unit, base_name).
    """
    s = text.strip().lower()
    
    # Pattern: "3 slices of bread"
    m = re.match(r"^(\d+(?:\.\d+)?)\s+(\w+)\s+of\s+(.+)$", s)
    if m:
        qty = float(m.group(1))
        unit = m.group(2).rstrip('s')
        return qty, unit, m.group(3).strip()
    
    # Pattern: "3 slices bread" (three words)
    m = re.match(r"^(\d+(?:\.\d+)?)\s+(\w+)\s+(\w+)$", s)
    if m:
        qty_str, word2, word3 = m.groups()
        qty = float(qty_str)
        
        # Check if word2 is a unit (e.g., "3 slices")
        if word2.rstrip('s') in UNIT_TO_GRAMS:
            return qty, word2.rstrip('s'), word3
        # Check if word2 is a beverage (e.g., "3 cokes")
        if word2.rstrip('s') in ["coke", "cola", "beer", "lager", "ale"]:
            unit = "can" if word2.rstrip('s') in ["coke", "cola"] else "pint"
            return qty, unit, word2.rstrip('s')
        # Check if word3 is a unit (e.g., "3 pieces bread" - unlikely but handle)
        return qty, None, f"{word2} {word3}"
    
    # Pattern: "3 cokes" (two words, beverage)
    m = re.match(r"^(\d+(?:\.\d+)?)\s+(\w+)$", s)
    if m:
        qty = float(m.group(1))
        word = m.group(2).rstrip('s')
        if word in ["coke", "cola", "beer", "lager", "ale"]:
            unit = "can" if word in ["coke", "cola"] else "pint"
            return qty, unit, word
    
    return 1.0, None, s


async def ai_parse_food_description(text: str) -> list[dict]:
    """
    Use AI to parse complex food descriptions like:
    - "bacon roll with two slices" → [{"food": "bacon roll", "quantity": 1}, {"food": "bacon", "quantity": 2, "unit": "slices"}]
    - "2 slices of pizza from a 12-inch pie" → [{"food": "pizza", "quantity": 2, "notes": "12-inch pie slice ~100g"}]
    
    Returns list of food dicts with name, quantity, and optional unit/notes.
    Falls back to simple parsing if AI unavailable.
    """
    # Try AI parsing first
    try:
        from app.services.llm_service import get_llm_service
        llm = get_llm_service()
        
        prompt = f"""Parse this food description into structured JSON:

"{text}"

Return exactly this format:
{{
  "foods": [
    {{"name": "food name", "quantity": 1, "unit": "optional unit", "notes": "optional notes"}}
  ]
}}

Rules:
- "bacon roll" = processed sausage roll (~60g)
- "bacon" = sliced bacon (~30g per slice)
- "slice" of pizza from 12" pie = ~100g
- "slice" of pizza from 16" pie = ~120g
- Combine multiple items separated by "and", "with", "+"
- If ambiguous, split into separate items
"""
        
        messages = [
            {"role": "system", "content": "Return only valid JSON, no extra text. You are a precise food parsing assistant."},
            {"role": "user", "content": prompt}
        ]
        
        result = await llm._call_llm(messages, max_tokens=200, stream=False)
        data = json.loads(result["response"])
        return data.get("foods", [{"name": text, "quantity": 1}])
    except Exception:
        pass
    
    # Fallback: simple "and" splitting with "with" support
    # "bacon roll with two slices" → bacon roll + bacon (2 slices)
    # "pizza with extra cheese" → pizza + cheese
    if " with " in text.lower():
        parts = text.lower().split(" with ")
        results = [{"name": parts[0].strip(), "quantity": 1}]
        for part in parts[1:]:
            # Parse "two slices" → quantity=2, name="slices"
            qty, unit, base_name = parse_quantity_unit(part.strip())
            if qty != 1 or unit:
                results.append({"name": base_name, "quantity": qty, "unit": unit})
            else:
                results.append({"name": part.strip(), "quantity": 1})
        return results
    
    if " and " in text.lower():
        items = text.lower().split(" and ")
        return [{"name": item.strip(), "quantity": 1} for item in items]
    
    return [{"name": text, "quantity": 1}]


async def normalize_food_description(text: str, model: str = "qwen/qwen3-32b", use_ollama: bool = False) -> list[dict]:
    """
    Use LLM to normalize food descriptions like:
    "3 cans of coke 2 bacon rolls and a packet of crisps" → 
    [{"item": "coke", "quantity": 3, "unit": "can"}, 
     {"item": "white roll", "quantity": 2},
     {"item": "bacon", "quantity": 4, "unit": "slices"},
     {"item": "crisps", "quantity": 1, "unit": "packet"}]
    
    Rules applied:
    - "bacon roll" → 1 white roll + 2 bacon slices per roll
    - "can of coke" → 330ml serving
    - Standardizes vocabulary to canonical names
    
    Args:
        text: Food description to normalize
        model: Model name (for OpenRouter) or Ollama model tag
        use_ollama: If True, use local Ollama instead of OpenRouter
    """
    import httpx
    
    prompt = f"""You are a food item parser. Extract structured data from the meal description.

Input: "{text}"

Return ONLY valid JSON in this exact format:
[
  {{"item": "food name in lowercase", "quantity": number, "unit": "optional unit"}}
]

Rules:
- "bacon roll" → two separate items: white roll (quantity) + bacon slices (quantity*2)
- "cans of coke" → unit="can"
- "packet of crisps" → unit="packet"
- "slices of bread" → unit="slices"
- If no quantity, assume 1
- Keep item names simple and canonical

Example:
Input: "3 cans of coke 2 bacon rolls and a packet of crisps"
Output: 
[
  {{"item": "coke", "quantity": 3, "unit": "can"}},
  {{"item": "white roll", "quantity": 2}},
  {{"item": "bacon", "quantity": 4, "unit": "slices"}},
  {{"item": "crisps", "quantity": 1, "unit": "packet"}}
]
"""
    
    if use_ollama:
        # Local Ollama API
        ollama_url = os.getenv("OLLAMA_URL", "http://192.168.0.211:11434")
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{ollama_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "Return only valid JSON, no extra text. You are precise."},
                            {"role": "user", "content": prompt}
                        ],
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                content = data["message"]["content"]
                items = json.loads(content)
                
                # Apply post-processing rules for compound foods
                processed = []
                for item in items:
                    if "bacon roll" in item.get("item", ""):
                        qty = item.get("quantity", 1)
                        processed.append({"item": "white roll", "quantity": qty})
                        processed.append({"item": "bacon", "quantity": qty * 2, "unit": "slices"})
                    else:
                        processed.append(item)
                return processed
            except Exception as e:
                print(f"Ollama error: {e}")
                return fallback_normalize(text)
    else:
        # OpenRouter API
        try:
            from app.services.llm_service import LLMService, LLMProvider
            llm = LLMService(provider=LLMProvider.OPENROUTER, model=model)
        except Exception:
            return fallback_normalize(text)
        
        messages = [
            {"role": "system", "content": "Return only valid JSON, no extra text. You are precise."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = await llm._call_llm(messages, max_tokens=500, stream=False)
            items = json.loads(result["response"])
            
            # Apply post-processing rules for compound foods
            processed = []
            for item in items:
                if "bacon roll" in item.get("item", ""):
                    qty = item.get("quantity", 1)
                    processed.append({"item": "white roll", "quantity": qty})
                    processed.append({"item": "bacon", "quantity": qty * 2, "unit": "slices"})
                else:
                    processed.append(item)
            return processed
        except Exception as e:
            print(f"LLM error: {e}")
            return fallback_normalize(text)


def fallback_normalize(text: str) -> list[dict]:
    """Simple regex-based fallback for food normalization."""
    import re
    
    # Handle "bacon roll" → white roll + 2 bacon slices
    text = re.sub(r'(\d+)\s*bacon\s*rolls?', r'\1 white rolls \1*2 bacon slices', text, flags=re.IGNORECASE)
    
    items = []
    
    # Pattern: "3 cans of coke" or "2 packets of crisps"
    pattern = r'(\d+)\s*(cans?|packets?|bags?)\s*(?:of\s*)?(\w+)'
    for match in re.finditer(pattern, text, re.IGNORECASE):
        qty, unit, item = match.groups()
        unit = unit.rstrip('s')  # normalize cans→can
        items.append({"item": item, "quantity": int(qty), "unit": unit})
    
    return items if items else [{"item": text, "quantity": 1}]


async def analyze_meal(foods, anchor_type="post_meal_spike"):
    """Analyze meal using FoodService with quantity parsing."""
    from app.core.database import db_manager, get_settings
    from app.food.service import FoodService
    
    settings = get_settings()
    db_manager.init_db(settings.database_url)
    
    # Get profile config
    if anchor_type not in PROFILE_CONFIGS:
        anchor_type = "post_meal_spike"
    config = PROFILE_CONFIGS[anchor_type]
    
    nutrition = []
    
    # First, try AI parsing for any complex descriptions
    # Support both list of strings and pre-normalized formats
    expanded_foods = []
    for food_item in foods:
        if isinstance(food_item, str):
            # Try normalization for complex descriptions
            if " with " in food_item.lower() or "plus" in food_item.lower() or len(food_item.split()) > 3:
                try:
                    normalized = await normalize_food_description(food_item)
                    expanded_foods.extend(normalized)
                    continue
                except Exception:
                    pass
            expanded_foods.append({"name": food_item, "quantity": 1})
        else:
            # Already a dict (from AI normalization)
            expanded_foods.append(food_item)
    
    for food_item in expanded_foods:
        food = food_item.get("name", food_item.get("item", food_item))
        qty = food_item.get("quantity", 1)
        # Try to parse unit from the item itself if present
        unit = food_item.get("unit")
        base_name = food
        
        # If we got a quantity from normalization, use it; otherwise parse from food string
        if qty == 1 and isinstance(food, str):
            qty, unit, base_name = parse_quantity_unit(food)
        
        async with db_manager.get_session() as session:
            service = FoodService(session)
            results = await service._search_local_off(base_name, limit=5)
            
            # Find best result with nutrition data
            r = None
            for candidate in results:
                carbs = candidate.get("carbs_per_100g")
                # Prefer results with valid carb data
                if carbs is not None and carbs > 0:
                    r = candidate
                    break
            # Fallback to first result if none have carbs
            if r is None and results:
                r = results[0]
            
            if r:
                carbs_per = r.get("carbs_per_100g")
                fat_per = r.get("fat_per_100g")
                serving_size = r.get("serving_size")
                
                # Use None defaults, not falsy defaults (0 is valid!)
                if carbs_per is None:
                    carbs_per = 25
                if fat_per is None:
                    fat_per = 5
                
                # Calculate serving grams
                if unit and unit in UNIT_TO_GRAMS:
                    serving_g = qty * UNIT_TO_GRAMS[unit]
                elif serving_size:
                    # Parse serving size like "43 g" or "1.5 ONZ (43 g)"
                    match = re.search(r"(\d+\.?\d*)\s*g", str(serving_size))
                    if match:
                        serving_g = float(match.group(1)) * qty
                    else:
                        serving_g = 100 * qty
                else:
                    serving_g = 100 * qty
                
                carbs = carbs_per * serving_g / 100
                fat = fat_per * serving_g / 100
            else:
                carbs, fat = 25 * qty, 5 * qty
            
            nutrition.append({"carbs": carbs, "fat": fat})
    
    total_carbs = sum(n["carbs"] for n in nutrition)
    total_fat = sum(n["fat"] for n in nutrition)
    bolus_est = total_carbs / config["carb_ratio"]
    
    # Build query string from original foods (could be strings or dicts)
    query_parts = []
    for food in foods:
        if isinstance(food, str):
            query_parts.append(food)
        elif isinstance(food, dict):
            item = food.get("item", food.get("name", str(food)))
            qty = food.get("quantity", 1)
            unit = food.get("unit", "")
            if unit:
                query_parts.append(f"{qty} {unit} {item}")
            else:
                query_parts.append(f"{qty} {item}")
    
    educational_units = round(bolus_est, 1)
    carb_ratio_val = round(config["carb_ratio"], 1)

    return {
        "query": " + ".join(query_parts),
        "profile": config["profile"]["anchor_label"],
        "totals": {
            "carbs_g": int(round(total_carbs)),
            "fat_g": int(round(total_fat)),
        },
        "educational_estimate": {
            "carb_ratio": carb_ratio_val,
            "units": educational_units,
            "note": f"Educational carb-ratio estimate: {educational_units} units at 1:{carb_ratio_val}",
        },
        "timing": {"peak_window": "30-45 min", "delayed_spike": "3-4 hours" if total_fat >= 15 else "none"},
        "recommendations": [
            f"Similar meals with ~{int(round(total_carbs))}g carbs and 1:{carb_ratio_val} ratio typically suggest around {educational_units} units — always follow your prescribed plan.",
            "Check BG at 30-45 min for peak.",
        ],
        "disclaimer": "Educational insight, not medical advice. Always consult your healthcare provider before making treatment decisions.",
    }

def _extract_json_array_or_object(text: str) -> Any:
    """Extract the first JSON array/object from an LLM response."""
    text = text.strip()
    if text.startswith("[") or text.startswith("{"):
        return json.loads(text)
    array_start = text.find("[")
    object_start = text.find("{")
    starts = [i for i in [array_start, object_start] if i >= 0]
    if not starts:
        raise ValueError("No JSON found in LLM response")
    start = min(starts)
    opener = text[start]
    closer = "]" if opener == "[" else "}"
    end = text.rfind(closer)
    if end < start:
        raise ValueError("Unclosed JSON in LLM response")
    return json.loads(text[start : end + 1])


async def local_ollama_parse_scenario(
    scenario: str,
    model: str = DEFAULT_LOCAL_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> list[dict[str, Any]]:
    """Parse a natural-language eating scenario using only local Ollama."""
    import httpx

    prompt = f"""Extract foods from this T1D scenario. Return ONLY a JSON array.

Scenario: {scenario!r}

Schema:
[
  {{"item":"canonical lowercase food name", "quantity": number, "unit": "optional serving unit", "search_terms": ["best database query", "backup query"]}}
]

Rules:
- Include only foods/drinks the user wants to consume.
- Do not estimate carbs.
- Use search_terms suitable for OpenFoodFacts/Postgres lookup.
- For ordinary coke/cola, include search terms ["coca cola", "coke", "cola"] and unit "can" if cans are mentioned.
- For diet/zero drinks, keep diet/zero in the item and search terms.
- If no quantity is stated, use 1.
"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{ollama_url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Return only valid JSON. No markdown. No prose."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"temperature": 0},
            },
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
    parsed = _extract_json_array_or_object(content)
    if isinstance(parsed, dict):
        parsed = parsed.get("foods", [])
    if not isinstance(parsed, list):
        raise ValueError("Scenario parser did not return a list")
    cleaned = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = str(item.get("item") or item.get("name") or "").strip().lower()
        if not name:
            continue
        qty = item.get("quantity", 1)
        try:
            qty = float(qty)
        except (TypeError, ValueError):
            qty = 1.0
        search_terms = item.get("search_terms") or [name]
        if isinstance(search_terms, str):
            search_terms = [search_terms]
        cleaned.append({
            "item": name,
            "quantity": qty,
            "unit": item.get("unit"),
            "search_terms": [str(term).strip().lower() for term in search_terms if str(term).strip()],
        })
    return cleaned or fallback_normalize(scenario)


def _serving_grams(quantity: float, unit: str | None, result: dict[str, Any]) -> float:
    if unit:
        unit_key = unit.lower().rstrip("s")
        if unit_key in UNIT_TO_GRAMS:
            return quantity * UNIT_TO_GRAMS[unit_key]
    serving_size = result.get("serving_size")
    serving_quantity = result.get("serving_quantity")
    if serving_quantity:
        return quantity * float(serving_quantity)
    if serving_size:
        match = re.search(r"(\d+\.?\d*)\s*g", str(serving_size), flags=re.IGNORECASE)
        if match:
            return quantity * float(match.group(1))
        ml_match = re.search(r"(\d+\.?\d*)\s*ml", str(serving_size), flags=re.IGNORECASE)
        if ml_match:
            return quantity * float(ml_match.group(1))
    return quantity * 100


def _is_bad_match(food: dict[str, Any], candidate: dict[str, Any]) -> bool:
    item = food["item"].lower()
    name = str(candidate.get("name") or "").lower()
    brand = str(candidate.get("brand") or "").lower()
    carbs = candidate.get("carbs_per_100g")
    haystack = f"{name} {brand}"
    wants_diet = any(token in item for token in ["diet", "zero", "sugar free"])
    is_cola = any(token in item for token in ["coke", "cola"])
    if is_cola and not wants_diet:
        if any(token in haystack for token in ["diet", "zero", "sugar free", "no sugar"]):
            return True
        if carbs is not None and carbs <= 1:
            return True
    if wants_diet and carbs is not None and carbs > 5:
        return True
    return False


async def search_food_evidence(food: dict[str, Any], limit: int = 8) -> dict[str, Any]:
    """Search local Postgres/OpenFoodFacts for one parsed food item."""
    from app.core.database import db_manager, get_settings
    from app.food.service import FoodService

    settings = get_settings()
    db_manager.init_db(settings.database_url)
    async with db_manager.get_session() as session:
        service = FoodService(session)
        candidates: list[dict[str, Any]] = []
        seen = set()
        for term in food.get("search_terms") or [food["item"]]:
            for row in await service._search_local_off(term, limit=limit):
                key = row.get("barcode") or row.get("name")
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(row)

    viable = [c for c in candidates if not _is_bad_match(food, c)] or candidates
    chosen = None
    for c in viable:
        if c.get("carbs_per_100g") is not None:
            chosen = c
            break
    chosen = chosen or (viable[0] if viable else None)
    quantity = float(food.get("quantity", 1))
    unit = food.get("unit")
    if not chosen:
        serving_g = quantity * 100
        return {"food": food, "match": None, "serving_g": serving_g, "carbs_g": 25 * quantity, "fat_g": 5 * quantity, "sugars_g": 0, "calories": None, "confidence": "fallback"}

    serving_g = _serving_grams(quantity, unit, chosen)
    scale = serving_g / 100
    carbs = float(chosen.get("carbs_per_100g") or 0) * scale
    fat = float(chosen.get("fat_per_100g") or 0) * scale
    sugars = float(chosen.get("sugars_per_100g") or 0) * scale
    calories_per_100g = chosen.get("calories_per_100g")
    calories = float(calories_per_100g) * scale if calories_per_100g is not None else None
    return {
        "food": food,
        "match": chosen,
        "serving_g": round(serving_g, 1),
        "carbs_g": round(carbs, 1),
        "fat_g": round(fat, 1),
        "sugars_g": round(sugars, 1),
        "calories": round(calories, 1) if calories is not None else None,
        "confidence": "local_db",
    }


def pick_random_profile(seed: int | None = None) -> tuple[str, dict[str, Any]]:
    rng = random.Random(seed)
    key = rng.choice(sorted(PROFILE_CONFIGS.keys()))
    return key, PROFILE_CONFIGS[key]


async def run_local_companion_loop(
    scenario: str,
    model: str = DEFAULT_LOCAL_MODEL,
    seed: int | None = None,
) -> dict[str, Any]:
    """All-local companion loop: LLM parse, Postgres search, deterministic totals, profile narration."""
    parsed_foods = await local_ollama_parse_scenario(scenario, model=model)
    profile_key, profile_config = pick_random_profile(seed)
    evidence = [await search_food_evidence(food) for food in parsed_foods]
    totals = {
        "carbs_g": round(sum(row["carbs_g"] for row in evidence), 1),
        "fat_g": round(sum(row["fat_g"] for row in evidence), 1),
        "sugars_g": round(sum(row["sugars_g"] for row in evidence), 1),
        "calories": round(sum(row["calories"] or 0 for row in evidence), 1),
    }
    carb_ratio = float(profile_config.get("carb_ratio") or 15)
    estimated_bolus = round(totals["carbs_g"] / carb_ratio, 1) if carb_ratio else None
    delayed = totals["fat_g"] >= 15
    sugar_heavy = totals["sugars_g"] >= 40
    suggestions = []
    if sugar_heavy:
        suggestions.append("Fast sugar load: expect an early rise, often visible within 15-30 minutes.")
    suggestions.append("Use your own insulin plan; this tool shows an educational calculation, not a dosing instruction.")
    suggestions.append(f"Profile context: {profile_config['profile']['anchor_label']} may change timing and follow-up risk.")
    if delayed:
        suggestions.append("Fat is high enough to watch for a delayed second rise around 3-4 hours.")
    suggestions.append("Check glucose trend around 30-45 minutes and again near 2 hours.")
    return {
        "scenario": scenario,
        "model": model,
        "selected_profile": {
            "key": profile_key,
            "label": profile_config["profile"]["anchor_label"],
            "carb_ratio": carb_ratio,
        },
        "parsed_foods": parsed_foods,
        "evidence": evidence,
        "totals": totals,
        "educational_estimate": {
            "carb_ratio": carb_ratio,
            "units": estimated_bolus,
            "note": f"{estimated_bolus} units at 1:{carb_ratio} (educational carb-ratio estimate, not a dosing instruction)",
        },
        "timing": {"early_spike": "15-30 min" if sugar_heavy else "30-60 min", "two_hour_risk": "high" if totals["carbs_g"] >= 80 else "moderate", "delayed_spike": "possible 3-4 hours" if delayed else "less likely"},
        "companion_suggestions": suggestions,
        "disclaimer": "Educational simulation insight only; not medical advice or a dosing prescription. Always consult your healthcare provider before making treatment decisions."
    }


def print_local_companion_report(result: dict[str, Any]) -> None:
    print("=" * 70)
    print("🤖 LOCAL T1D COMPANION LOOP")
    print("=" * 70)
    print(f"Scenario: {result['scenario']}")
    profile = result["selected_profile"]
    print(f"Random sim profile: {profile['label']} ({profile['key']}), carb ratio 1:{profile['carb_ratio']}")
    print("\nFoods parsed + local DB evidence:")
    for row in result["evidence"]:
        food = row["food"]
        match = row.get("match") or {}
        name = match.get("name") or "fallback estimate"
        print(f"  - {food['quantity']:g} {food.get('unit') or ''} {food['item']}: {row['carbs_g']}g carbs, {row['fat_g']}g fat, {row['sugars_g']}g sugars → {name}")
    totals = result["totals"]
    print("\nTotals:")
    print(f"  Carbs: {totals['carbs_g']}g | Fat: {totals['fat_g']}g | Sugars: {totals['sugars_g']}g | Calories: {totals['calories']} kcal")
    estimate = result["educational_estimate"]
    print(f"  Educational carb-ratio estimate: {estimate['units']} units at 1:{estimate['carb_ratio']}")
    print("\nLikely pattern:")
    print(f"  Early spike: {result['timing']['early_spike']}")
    print(f"  2-hour risk: {result['timing']['two_hour_risk']}")
    print(f"  Delayed spike: {result['timing']['delayed_spike']}")
    print("\nCompanion suggestions:")
    for suggestion in result["companion_suggestions"]:
        print(f"  • {suggestion}")
    print(f"\n{result['disclaimer']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.t1d_companion.fast_analysis \"scenario...\" [anchor_type] [--ollama] [--local-loop] [--json]")
        sys.exit(1)
    
    use_ollama = "--ollama" in sys.argv
    use_local_loop = "--local-loop" in sys.argv
    output_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    
    foods_text = args[0]
    anchor = args[1] if len(args) > 1 else "post_meal_spike"
    
    if use_local_loop:
        local_result = asyncio.run(run_local_companion_loop(foods_text))
        if output_json:
            print(json.dumps(local_result, indent=2, default=str))
        else:
            print_local_companion_report(local_result)
        sys.exit(0)

    # Run the async analysis
    async def main():
        if use_ollama:
            try:
                foods_normalized = await normalize_food_description(foods_text, model=DEFAULT_LOCAL_MODEL, use_ollama=True)
                result = await analyze_meal(foods_normalized, anchor)
            except Exception as e:
                print(f"Ollama error: {e}")
                result = await analyze_meal([foods_text], anchor)
        else:
            result = await analyze_meal([foods_text], anchor)
        return result
    
    result = asyncio.run(main())
    
    print("="*70)
    print(f"🤖 T1D COMPANION: {result['query'].upper()}")
    print("="*70)
    print(f"\nProfile: {result['profile']}")
    print(f"\n📊 TOTALS:")
    print(f"   Carbs: {result['totals']['carbs_g']}g")
    print(f"   Fat: {result['totals']['fat_g']}g")
    estimate = result.get("educational_estimate", {})
    if estimate:
        print(f"\n📋 EDUCATIONAL ESTIMATE:")
        print(f"   {estimate['note']}")
    print(f"\n⏱️  TIMING:")
    print(f"   Peak window: {result['timing']['peak_window']}")
    print(f"   Delayed spike: {result['timing']['delayed_spike']}")
    print(f"\n💡 OBSERVATIONS:")
    for r in result['recommendations']:
        print(f"   • {r}")
    print(f"\n{result['disclaimer']}")