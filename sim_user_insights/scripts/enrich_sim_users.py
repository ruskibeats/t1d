#!/usr/bin/env python3
"""
Enrich simulated T1D users with real OpenFoodFacts nutrition data.

For each anchor type / simulated profile:
1. Loads 90-day food history
2. For each unique food, queries Postgres OpenFoodFacts for real nutrition (carbs, fat, protein, kcal per 100g)
3. Merges matched OF data into each history entry with computed macros per assumed serving
4. Enriches profile configs with full PatientConfig parameters and anchor ranges
5. Produces a comprehensive per-anchor enriched dataset

Output: sim_user_insights/outputs/sim_users_enriched.json
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

# ── Paths ──
ROOT = Path(__file__).resolve().parents[2]
PROFILE_CONFIGS = ROOT / "data" / "profile_configs.json"
HISTORY_PRIMARY = ROOT / "data" / "food_history_90d_enhanced.json"
HISTORY_FALLBACK = ROOT / "data" / "food_history_90d.json"
INSIGHTS_PATH = ROOT / "sim_user_insights" / "outputs" / "sim_user_insights.json"
OUTPUT = ROOT / "sim_user_insights" / "outputs" / "sim_users_enriched.json"

# ── OpenFoodFacts field aliases (from _search_local_off response shape) ──
OFF_FIELDS = [
    "name", "brand", "barcode", "carbs_per_100g", "protein_per_100g",
    "fat_per_100g", "calories_per_100g", "fiber_per_100g", "sugars_per_100g",
    "sodium_per_100g", "serving_size",
]


def _num(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _round(val: float, digits: int = 1) -> float:
    return round(val, digits)


# ── Serving estimation (mirrors local_loop serving_amount logic) ──
UNIT_TO_GRAMS: dict[str, float] = {
    "slice": 30, "slices": 30,
    "pieces": 100, "piece": 100,
    "cup": 240, "cups": 240,
    "tbsp": 15, "tablespoon": 15, "tablespoons": 15,
    "can": 330, "cans": 330,
    "pint": 568, "pints": 568,
    "bowl": 300, "bowls": 300,
    "plate": 350, "plates": 350,
    "serving": 200, "servings": 200,
    "large": 250, "medium": 180, "small": 120,
    "glass": 250, "bottle": 500, "packet": 50,
}


def estimate_serving_g(food_name: str, food_source: str = "unknown") -> float:
    """Heuristic serving estimate from food name/type."""
    name = food_name.lower()
    if "pizza" in name:
        return 100  # per slice
    if "lager" in name or "beer" in name or "ale" in name:
        return 568  # pint
    if "smoothie" in name:
        return 300
    if "salad" in name:
        return 200
    if "sandwich" in name or "wrap" in name:
        return 200
    if "soup" in name:
        return 300
    if "steak" in name:
        return 250
    if "burger" in name:
        return 200
    if "burrito" in name or "taco" in name:
        return 300
    if "pasta" in name or "noodle" in name or "lo mein" in name:
        return 300
    if "rice" in name:
        return 200
    if "ice cream" in name:
        return 100
    if "cookie" in name:
        return 40
    if "chocolate" in name:
        return 50
    if "chips" in name or "crisps" in name:
        return 50
    if "oatmeal" in name or "porridge" in name or "cereal" in name:
        return 200
    if "egg" in name:
        return 100
    if "toast" in name or "bread" in name:
        return 50
    return 200


# ── Search OpenFoodFacts via Postgres ──
async def search_off(term: str) -> dict[str, Any] | None:
    """Query Postgres openfoodfacts_products for a food term. Returns best match dict or None."""
    try:
        from app.core.database import db_manager, get_settings
        from app.food.service import FoodService, _assess_food_dict_quality
        from app.db.models import OpenFoodFactsProduct
        from sqlalchemy import select, func, text

        db_manager.init_db(get_settings().database_url)
        async with db_manager.get_session() as session:
            stmt = (
                select(OpenFoodFactsProduct, func.similarity(OpenFoodFactsProduct.product_name, term).label("similarity"))
                .where(
                    OpenFoodFactsProduct.product_name.isnot(None),
                    OpenFoodFactsProduct.carbs_100g.isnot(None),
                )
                .order_by(
                    func.similarity(OpenFoodFactsProduct.product_name, term).desc(),
                    OpenFoodFactsProduct.nutriscore_score.asc().nullslast(),
                )
                .limit(3)
            )
            result = await session.execute(stmt)
            rows = list(result.all())
            if not rows:
                return None

            # Pick best non-trivial match
            for product, similarity in rows:
                name = (product.product_name or "").lower()
                # Skip obvious mismatches
                if len(term) >= 4:
                    term_words = set(term.lower().split())
                    name_words = set(name.split())
                    if not term_words & name_words and similarity < 0.2:
                        continue
                return {
                    "source": "openfoodfacts_local",
                    "name": product.product_name,
                    "brand": product.brands,
                    "barcode": product.code,
                    "carbs_per_100g": _num(product.carbs_100g),
                    "protein_per_100g": _num(product.proteins_100g),
                    "fat_per_100g": _num(product.fat_100g),
                    "calories_per_100g": _num(product.energy_kcal_100g),
                    "serving_size": product.serving_size,
                    "fiber_per_100g": _num(product.fiber_100g),
                    "sugars_per_100g": _num(product.sugars_100g),
                    "sodium_per_100g": _num(product.sodium_100g),
                    "_similarity": round(similarity, 3) if similarity else 0,
                }
    except Exception as e:
        print(f"  [WARN] OF search failed for '{term}': {e}")
        return None


async def enrich_history_row(row: dict[str, Any], of_cache: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    """Enrich one history row with matched OpenFoodFacts nutrition."""
    food_name = str(row.get("food") or "")
    of_match = of_cache.get(food_name.lower())

    # Estimate serving grams
    hist_carbs = _num(row.get("carb_estimate_g"))
    hist_fat = _num(row.get("fat_g"))

    if of_match and of_match.get("carbs_per_100g") and of_match["carbs_per_100g"] > 0:
        # Derive serving size from historical carb estimate
        carbs_100g = of_match["carbs_per_100g"]
        derived_serving = (hist_carbs / carbs_100g) * 100 if hist_carbs > 0 and carbs_100g > 0 else estimate_serving_g(food_name)
        if derived_serving < 10 or derived_serving > 1000:
            derived_serving = estimate_serving_g(food_name)
    else:
        derived_serving = estimate_serving_g(food_name)

    # Compute macros from matched OF data
    of_nutrition = None
    if of_match:
        carbs_100g = _num(of_match.get("carbs_per_100g"))
        fat_100g = _num(of_match.get("fat_per_100g"))
        protein_100g = _num(of_match.get("protein_per_100g"))
        kcal_100g = _num(of_match.get("calories_per_100g"))
        sugar_100g = _num(of_match.get("sugars_per_100g"))
        fiber_100g = _num(of_match.get("fiber_per_100g"))

        amt = derived_serving
        of_nutrition = {
            "carbs_g": _round(carbs_100g * amt / 100),
            "fat_g": _round(fat_100g * amt / 100),
            "protein_g": _round(protein_100g * amt / 100),
            "kcal": _round(kcal_100g * amt / 100, 0),
            "sugars_g": _round(sugar_100g * amt / 100),
            "fiber_g": _round(fiber_100g * amt / 100),
            "serving_g": _round(amt, 0),
        }

    # CGM impact
    cgm = row.get("cgm_impact") or {}
    safety = row.get("safety_flags") or {}

    enriched = dict(row)
    enriched["of_match"] = of_match
    enriched["of_nutrition"] = of_nutrition
    enriched["estimated_serving_g"] = _round(derived_serving, 0)
    enriched["computed"] = of_nutrition

    # Cross-reference historical estimate vs OF computed
    if of_nutrition:
        enriched["carb_delta_pct"] = _round(
            (hist_carbs - of_nutrition["carbs_g"]) / of_nutrition["carbs_g"] * 100
        ) if of_nutrition["carbs_g"] > 0 else None

    return enriched


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


async def main():
    print("=" * 65)
    print("Sim User Enrichment Pipeline")
    print("=" * 65)

    # Load inputs
    profiles = _load_json(PROFILE_CONFIGS)
    history_path = HISTORY_PRIMARY if HISTORY_PRIMARY.exists() else HISTORY_FALLBACK
    rows = _load_json(history_path)
    insights = _load_json(INSIGHTS_PATH) if INSIGHTS_PATH.exists() else None

    print(f"Loaded: {len(profiles)} profiles, {len(rows)} history rows")

    # Collect unique food names per anchor, also globally deduped
    unique_foods: set[str] = set()
    for row in rows:
        name = str(row.get("food") or "").lower().strip()
        if name and name != "unknown" and name != "none":
            unique_foods.add(name)

    print(f"Unique food names to look up: {len(unique_foods)}")

    # Search OpenFoodFacts for each unique food (with cache)
    of_cache: dict[str, dict[str, Any] | None] = {}
    batch = sorted(unique_foods)
    found, failed = 0, 0
    for i, food_name in enumerate(batch):
        if i % 20 == 0 and i > 0:
            print(f"  Progress: {i}/{len(batch)} (found={found}, failed={failed})")
        match = await search_off(food_name)
        of_cache[food_name] = match
        if match:
            found += 1
        else:
            failed += 1

    print(f"\nOF search complete: {found} matched, {failed} not found")

    # Enrich history rows
    print("Enriching history rows...")
    enriched_rows = await asyncio.gather(*[
        enrich_history_row(row, of_cache) for row in rows
    ])

    # Group enriched rows by anchor type
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in enriched_rows:
        anchor = row.get("anchor_type")
        if anchor:
            grouped[str(anchor)].append(row)

    # Build per-anchor enriched output
    anchors_out = []
    for anchor_type in sorted(profiles):
        profile = profiles[anchor_type]
        history = grouped.get(anchor_type, [])

        # Aggregate OF match stats for this anchor
        of_matched = [h for h in history if h.get("of_match")]
        of_missed = [h for h in history if not h.get("of_match")]
        of_match_rate = len(of_matched) / len(history) if history else 0

        # Macro distributions from OF-computed data
        of_carbs = [_num(h.get("of_nutrition", {}).get("carbs_g")) for h in of_matched]
        of_fat = [_num(h.get("of_nutrition", {}).get("fat_g")) for h in of_matched]
        of_protein = [_num(h.get("of_nutrition", {}).get("protein_g")) for h in of_matched]
        of_kcal = [_num(h.get("of_nutrition", {}).get("kcal")) for h in of_matched]

        # Historical macro distributions
        hist_carbs = [_num(r.get("carb_estimate_g")) for r in history]
        hist_fat = [_num(r.get("fat_g")) for r in history]

        # CGM impact distributions
        peak_deltas = [_num(r.get("cgm_impact", {}).get("expected_peak_delta")) for r in history]
        peak_times = [_num(r.get("cgm_impact", {}).get("peak_time_minutes")) for r in history]
        fat_delays = [_num(r.get("cgm_impact", {}).get("fat_delay_hours")) for r in history]
        conf_scores = [_num(r.get("confidence_score")) for r in history]

        # Safety flags
        delayed_risk = sum(1 for r in history if r.get("safety_flags", {}).get("delayed_risk"))
        high_carb = sum(1 for r in history if r.get("safety_flags", {}).get("high_carb"))
        high_fat = sum(1 for r in history if r.get("safety_flags", {}).get("high_fat"))

        # Top foods with OF data
        food_name_counts = Counter(str(r.get("food")) for r in history)
        top_foods_enriched = []
        for food_name, count in food_name_counts.most_common(15):
            match = of_cache.get(food_name.lower())
            top_foods_enriched.append({
                "food": food_name,
                "count": count,
                "of_match": {
                    "name": match.get("name") if match else None,
                    "carbs_per_100g": match.get("carbs_per_100g") if match else None,
                    "fat_per_100g": match.get("fat_per_100g") if match else None,
                    "kcal_per_100g": match.get("calories_per_100g") if match else None,
                    "protein_per_100g": match.get("protein_per_100g") if match else None,
                } if match else None,
            })

        # Find the matching insight entry
        anchor_insight = None
        if insights:
            for a in insights.get("anchors", []):
                if a.get("anchor_type") == anchor_type:
                    anchor_insight = a
                    break

        entry = {
            "anchor_type": anchor_type,
            "profile": profile,
            "history_meal_count": len(history),
            "of_match_rate": round(of_match_rate, 3),
            "top_foods_enriched": top_foods_enriched,
            "distributions": {
                "of_carbs_g_per_meal": {
                    "median": _round(median(of_carbs)) if of_carbs else None,
                    "p10": _round(sorted(of_carbs)[len(of_carbs)//10]) if len(of_carbs) >= 10 else None,
                    "p90": _round(sorted(of_carbs)[-1 - len(of_carbs)//10]) if len(of_carbs) >= 10 else None,
                    "range": [min(of_carbs), max(of_carbs)] if of_carbs else None,
                },
                "of_fat_g_per_meal": {
                    "median": _round(median(of_fat)) if of_fat else None,
                    "range": [min(of_fat), max(of_fat)] if of_fat else None,
                },
                "of_kcal_per_meal": {
                    "median": _round(median(of_kcal), 0) if of_kcal else None,
                    "range": [min(of_kcal), max(of_kcal)] if of_kcal else None,
                },
                "hist_carbs_g_per_meal": {
                    "median": _round(median(hist_carbs)) if hist_carbs else None,
                    "range": [min(hist_carbs), max(hist_carbs)] if hist_carbs else None,
                },
                "expected_peak_delta_mg_dl": {
                    "median": _round(median(peak_deltas)) if peak_deltas else None,
                    "range": [min(peak_deltas), max(peak_deltas)] if peak_deltas else None,
                },
                "peak_time_minutes": {
                    "median": _round(median(peak_times)) if peak_times else None,
                    "range": [min(peak_times), max(peak_times)] if peak_times else None,
                },
                "fat_delay_hours": {
                    "median": _round(median(fat_delays)) if fat_delays else None,
                    "range": [min(fat_delays), max(fat_delays)] if fat_delays else None,
                },
                "confidence_score": {
                    "median": _round(median(conf_scores)) if conf_scores else None,
                    "range": [min(conf_scores), max(conf_scores)] if conf_scores else None,
                },
            },
            "safety_flag_rates": {
                "delayed_risk": round(delayed_risk / len(history), 3) if history else 0,
                "high_carb": round(high_carb / len(history), 3) if history else 0,
                "high_fat": round(high_fat / len(history), 3) if history else 0,
            },
            "patterns": anchor_insight.get("patterns", []) if anchor_insight else [],
            "sample_history_rows": history[:5] if history else [],
        }
        anchors_out.append(entry)

    output = {
        "schema_version": "sim_users_enriched.v1",
        "generated_at": datetime.now().isoformat(),
        "source_history": str(history_path.relative_to(ROOT)),
        "source_profiles": str(PROFILE_CONFIGS.relative_to(ROOT)),
        "of_search_stats": {
            "unique_foods_searched": len(unique_foods),
            "matched": found,
            "not_found": failed,
            "match_rate": round(found / len(unique_foods), 3) if unique_foods else 0,
        },
        "anchor_count": len(anchors_out),
        "total_history_rows": len(rows),
        "anchors": anchors_out,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {OUTPUT}")
    print(f"  {len(anchors_out)} anchors")
    print(f"  {len(rows)} history rows enriched")
    print(f"  OF match rate: {found}/{len(unique_foods)} unique foods ({round(100*found/len(unique_foods), 1)}%)")


if __name__ == "__main__":
    asyncio.run(main())