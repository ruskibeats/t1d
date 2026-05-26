#!/usr/bin/env python3
"""12-Factor Agents compliant T1D Companion pipeline.

See README.md in parent directory for full documentation.

This module provides a testable, modular pipeline following:
- Factor 3: Own your context window
- Factor 5: Unify execution state and business state  
- Factor 8: Own your control flow
- Factor 12: Make your agent a stateless reducer
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random as rand
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Set up paths
REPO_ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(REPO_ROOT))

# Load environment
_env = REPO_ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.core.database import db_manager, get_settings
from app.food.service import FoodService
from app.services.llm_service import LLMProvider
from app.services.llm_call import LLMCapture, FirstCallLLMRouter
from app.simulator.schemas import AnchorType
from sim_user_insights.scripts.forecast_engine import MealTotals, ForecastStage, ForecastResult
from sim_user_insights.scripts.forecast_renderer import render_forecast, build_historical_timeline
from sim_user_insights.scripts.sim_current_reading import generate_current_reading

# ── State Management (Factor 5) ──

@dataclass
class CompanionState:
    """Unified execution and business state.
    
    Enables pause/resume and stateful reducer pattern.
    Note: forecast uses ForecastResult for strong typing; profile_config is PatientConfig
    (Pydantic BaseModel) for backwards compatibility with simulator schemas.
    """
    scenario: str
    anchor_type: str | None = None
    
    # Stage outputs
    foods: list = field(default_factory=list)
    profile_config: Any = None  # PatientConfig (Pydantic)
    profile_json: dict = field(default_factory=dict)
    sim_reading: dict = field(default_factory=dict)
    evidence_items: list = field(default_factory=list)
    totals: dict = field(default_factory=dict)
    forecast: ForecastResult | None = None  # Typed: ForecastResult from forecast_engine
    similar_meals: list = field(default_factory=list)
    historical_timeline: list = field(default_factory=list)
    historical_summary: dict = field(default_factory=dict)
    llm_responses: dict = field(default_factory=dict)
    response: str = ""
    
    # Metadata
    question_mode: str = "forecast"
    safety_rule: str = ""
    # Carb estimation metadata
    total_carbs_g_range: tuple[float, float] = (0.0, 0.0)
    confidence_overall: str = "medium"
    # Clarification protocol
    clarification_needed: bool = False
    clarification_prompt: str | None = None
    clarification_answer: str | None = None

    def to_context(self) -> dict[str, Any]:
        """Build context for LLM stages (Factor 3)."""
        return {
            "scenario": self.scenario,
            "anchor_type": self.anchor_type,
            "current_glucose": self.sim_reading.get("cgm_displayed_mg_dl"),
            "profile": self.profile_json,
            "foods": self.foods,
            "totals": self.totals,
            "evidence_items": self.evidence_items,
            "total_carbs_g_range": self.total_carbs_g_range,
            "confidence_overall": self.confidence_overall,
        }


# ── Stage Functions (Factor 8) ──

async def stage_select_profile(state: CompanionState, seed: int = 42) -> CompanionState:
    """Select simulated user profile and generate current reading.
    
    Returns new state (immutable pattern for testability).
    """
    from app.t1d_companion.local_loop import pick_profile_by_anchor
    
    if state.anchor_type is None:
        random_anchor = rand.choice(list(AnchorType))
        config, profile_json = pick_profile_by_anchor(random_anchor)
    else:
        config, profile_json = pick_profile_by_anchor(state.anchor_type)
    
    sim_reading = generate_current_reading(
        config.anchor_type.value, config, current_hour=19
    )
    
    return CompanionState(
        scenario=state.scenario,
        anchor_type=config.anchor_type.value,
        foods=state.foods,
        profile_config=config,
        profile_json=profile_json,
        sim_reading=sim_reading,
        question_mode=state.question_mode,
        safety_rule=state.safety_rule,
    )


async def stage_parse_foods(state: CompanionState, llm_call: Callable) -> CompanionState:
    """Parse scenario into structured food items.
    
    Uses both LLM parsing and deterministic fallback.
    """
    from app.t1d_companion.local_loop import (
        _extract_json, _load_prompt, _normalise_food_dict, fallback_parse_scenario
    )
    
    # LLM parsing attempt
    try:
        raw = await llm_call([
            {"role": "system", "content": _load_prompt("parser_system.txt", "Return JSON")},
            {"role": "user", "content": state.scenario},
        ], 300)
        if raw:
            data = _extract_json(raw)
            llm_items = data if isinstance(data, list) else data.get("foods", [])
            foods = [_normalise_food_dict(x) for x in llm_items if isinstance(x, dict)]
            if foods:
                return CompanionState(
                    **{**asdict(state), "foods": foods, "llm_responses": {**state.llm_responses, "parse": raw}}
                )
    except Exception:
        pass
    
    # Fallback to deterministic parsing
    foods = fallback_parse_scenario(state.scenario)
    return CompanionState(
        **{**asdict(state), "foods": foods}
    )


async def stage_db_lookup(state: CompanionState) -> CompanionState:
    """Search OpenFoodFacts and compute nutrition."""
    from app.t1d_companion.local_loop import (
        calculate_food_evidence, search_food_candidates, ParsedFood
    )

    # Helper: state.foods may contain ParsedFood objects or dicts (after asdict).
    # Normalize to ParsedFood for uniform access.
    def _to_parsed_food(food):
        if isinstance(food, ParsedFood):
            return food
        return ParsedFood(
            item=food.get("item", "unknown"),
            quantity=food.get("quantity", 1.0),
            unit=food.get("unit"),
            search_terms=food.get("search_terms", []),
        )

    total_carb_min = 0.0
    total_carb_max = 0.0
    conf_levels = []
    confidence_overall = "medium"
    
    # Known fast-food/reference values for items with unreliable OFF data
    FAST_FOOD_KNOWN_VALUES = {
        "big mac": {"carbs_100g": 50.0, "fat_100g": 32.2, "protein_100g": 27.8, "name": "Big Mac (McDonalds)", "serving_g": 90},
        "burger": {"carbs_100g": 45.0, "fat_100g": 30.0, "protein_100g": 25.0, "name": "Burger (generic)", "serving_g": 100},
        "fries": {"carbs_100g": 44.0, "fat_100g": 16.0, "protein_100g": 4.0, "name": "French Fries", "serving_g": 150},
        "french fries": {"carbs_100g": 44.0, "fat_100g": 16.0, "protein_100g": 4.0, "name": "French Fries", "serving_g": 150},
        "guinness": {"carbs_100g": 4.4, "fat_100g": 0.0, "protein_100g": 0.7, "name": "Guinness (pint)", "serving_g": 568},
        "beer": {"carbs_100g": 3.0, "fat_100g": 0.0, "protein_100g": 0.5, "name": "Beer (generic)", "serving_g": 330},
        "pint": {"carbs_100g": 3.0, "fat_100g": 0.0, "protein_100g": 0.5, "name": "Pint (generic)", "serving_g": 568},
    }
    
    try:
        settings = get_settings()
        db_manager.init_db(settings.database_url)
        
        evidence_items = []
        async with db_manager.get_session() as session:
            service = FoodService(session)
            for food_raw in state.foods:
                food = _to_parsed_food(food_raw)
                # Check if we have known values for this food
                food_item_raw = food.item.lower()
                search_keys = [food_item_raw]
                for term in food.search_terms:
                    search_keys.append(term.lower())
                    search_keys.append(term.lower().rstrip("s"))
                search_keys.append(food_item_raw.rstrip("s"))
                
                known_match = None
                for key in search_keys:
                    if key in FAST_FOOD_KNOWN_VALUES:
                        known_match = FAST_FOOD_KNOWN_VALUES[key]
                        break
                
                if known_match:
                    # Use known values for unreliable OFF matches
                    amount = known_match.get("serving_g", 100.0)
                    computed = {
                        "carbs_g": round(known_match["carbs_100g"] * amount / 100, 1),
                        "fat_g": round(known_match["fat_100g"] * amount / 100, 1),
                        "sugars_g": 0.0,
                        "protein_g": round(known_match["protein_100g"] * amount / 100, 1),
                        "kcal": 0,
                    }
                    evidence_items.append({
                        "parsed": {"item": food.item, "quantity": food.quantity, "unit": food.unit},
                        "selected_match": {"name": known_match["name"]},
                        "computed": computed,
                        "confidence": "medium",
                        "warnings": ["Using known nutrition values for accuracy"],
                    })
                else:
                    # Use database lookup
                    candidates = await search_food_candidates(service, food)
                    evidence = calculate_food_evidence(food, candidates)
                    evidence_items.append(asdict(evidence))
        
        # Compute totals and carb range
        totals = {"carbs_g": 0.0, "fat_g": 0.0, "sugars_g": 0.0, "protein_g": 0.0, "kcal": 0.0}
        for item in evidence_items:
            if item.get("computed"):
                for k in totals:
                    totals[k] += item["computed"].get(k, 0.0)
            # Aggregate carb range from per-food evidence
            cmin, cmax = item.get("carb_range_g", (0.0, 0.0))
            if (cmin, cmax) == (0.0, 0.0) and item.get("computed", {}).get("carbs_g") is not None:
                point = item["computed"]["carbs_g"]
                cmin = round(point * 0.9, 1)
                cmax = round(point * 1.1, 1)
            total_carb_min += cmin
            total_carb_max += cmax
            conf_levels.append(item.get("confidence", "low"))
        totals = {k: round(v, 1) for k, v in totals.items()}
        # Overall confidence: high only if all foods high; low if any low; else medium
        if all(c == "high" for c in conf_levels):
            confidence_overall = "high"
        elif any(c == "low" for c in conf_levels):
            confidence_overall = "low"
        else:
            confidence_overall = "medium"
    except Exception as e:
        logger.exception("stage_db_lookup failed - falling back to reference data")
        
        # Fallback: use reference data from find_reference_rows
        from app.t1d_companion.local_loop import find_reference_rows, ParsedFood, _load_local_food_db
        
        # First check if we have known fast-food reference values  
        # Per 100g values based on McDonalds nutrition facts:
        # Big Mac (~90g): 45g carbs, 29g fat, 25g protein per sandwich
        # Large Fries (~150g): 66g carbs, 24g fat, 6g protein per serving
        FAST_FOOD_KNOWN_VALUES = {
            "big mac": {"carbs_100g": 50.0, "fat_100g": 32.2, "protein_100g": 27.8, "name": "Big Mac (McDonalds)", "serving_g": 90},
            "burger": {"carbs_100g": 45.0, "fat_100g": 30.0, "protein_100g": 25.0, "name": "Burger (generic)", "serving_g": 100},
            "fries": {"carbs_100g": 44.0, "fat_100g": 16.0, "protein_100g": 4.0, "name": "French Fries", "serving_g": 150},
            "french fries": {"carbs_100g": 44.0, "fat_100g": 16.0, "protein_100g": 4.0, "name": "French Fries", "serving_g": 150},
            "guinness": {"carbs_100g": 4.4, "fat_100g": 0.0, "protein_100g": 0.7, "name": "Guinness (pint)", "serving_g": 568},
            "beer": {"carbs_100g": 3.0, "fat_100g": 0.0, "protein_100g": 0.5, "name": "Beer (generic)", "serving_g": 330},
            "pint": {"carbs_100g": 3.0, "fat_100g": 0.0, "protein_100g": 0.5, "name": "Pint (generic)", "serving_g": 568},
        }
        
        evidence_items = []
        totals = {"carbs_g": 0.0, "fat_g": 0.0, "sugars_g": 0.0, "protein_g": 0.0, "kcal": 0.0}

        for food_raw in state.foods:
            food = _to_parsed_food(food_raw)
            # Try multiple key variations to match fast-food lookup
            # Check the raw item name first
            food_item_raw = food.item.lower()

            # Also check search terms and common variations
            search_keys = [food_item_raw]
            for term in food.search_terms:
                search_keys.append(term.lower())
                # Add singular form too
                search_keys.append(term.lower().rstrip("s"))
            
            # Also check the original item with different forms
            search_keys.append(food_item_raw.rstrip("s"))
            
            match_data = None
            for key in search_keys:
                if key in FAST_FOOD_KNOWN_VALUES:
                    match_data = FAST_FOOD_KNOWN_VALUES[key]
                    break
            
            if match_data:
                # Use known fast-food values with correct serving sizes
                amount = match_data.get("serving_g", 100.0)
                
                computed = {
                    "carbs_g": round(match_data["carbs_100g"] * amount / 100, 1),
                    "fat_g": round(match_data["fat_100g"] * amount / 100, 1),
                    "sugars_g": 0.0,
                    "protein_g": round(match_data["protein_100g"] * amount / 100, 1),
                    "kcal": 0,
                }
                
                evidence_items.append({
                    "parsed": {"item": food.item, "quantity": food.quantity},
                    "selected_match": {"name": match_data["name"]},
                    "computed": computed,
                    "confidence": "low",
                    "warnings": ["Using known nutrition values for accuracy"],
                })
                for k in totals:
                    totals[k] += computed.get(k, 0.0)
                # Known values: use ±10% as range
                cmin = round(computed["carbs_g"] * 0.9, 1)
                cmax = round(computed["carbs_g"] * 1.1, 1)
                total_carb_min += cmin
                total_carb_max += cmax
                conf_levels.append("low")
            else:
                # Try reference rows as before
                refs = find_reference_rows(food)
                if refs:
                    ref = refs[0]
                    amount = 100.0
                    item_lower = food.item.lower()
                    if "burger" in item_lower:
                        amount = 100.0
                    elif "fries" in item_lower or "chips" in item_lower:
                        amount = 150.0
                    
                    computed = {
                        "carbs_g": round((ref.get("carbs_100g") or 0) * amount / 100, 1),
                        "fat_g": round((ref.get("fat_100g") or 0) * amount / 100, 1),
                        "sugars_g": 0.0,
                        "protein_g": round((ref.get("protein_100g") or 0) * amount / 100, 1),
                        "kcal": 0,
                    }
                    
                    evidence_items.append({
                        "parsed": {"item": food.item, "quantity": food.quantity},
                        "selected_match": {"name": ref.get("name")},
                        "computed": computed,
                        "confidence": "low",
                        "warnings": ["Database unavailable; using reference data"],
                    })
                    for k in totals:
                        totals[k] += computed.get(k, 0.0)
                    cmin = round(computed["carbs_g"] * 0.9, 1)
                    cmax = round(computed["carbs_g"] * 1.1, 1)
                    total_carb_min += cmin
                    total_carb_max += cmax
                    conf_levels.append("low")
                else:
                    evidence_items.append({
                        "parsed": {"item": food.item, "quantity": food.quantity},
                        "selected_match": None,
                        "computed": None,
                        "confidence": "none",
                        "warnings": ["No reference match found"],
                    })
                    conf_levels.append("none")

        # Fallback overall confidence
        if all(c == "low" for c in conf_levels):
            confidence_overall_fallback = "low"
        elif any(c == "none" for c in conf_levels):
            confidence_overall_fallback = "low"
        else:
            confidence_overall_fallback = "medium"

        totals = {k: round(v, 1) for k, v in totals.items()}

    return CompanionState(
        **{**asdict(state),
            "evidence_items": evidence_items,
            "totals": totals,
            "total_carbs_g_range": (round(total_carb_min, 1), round(total_carb_max, 1)),
            "confidence_overall": confidence_overall,
        }
    )


def _clarification_priority(item: str) -> float:
    """Prioritise clarification for likely carb-driver foods.

    This avoids asking about protein/non-starchy veg when noisy DB candidates
    create an artificially wide carb range.
    """
    item_l = item.lower()
    carb_driver_terms = (
        "potato", "rice", "pasta", "noodle", "bread", "toast", "bun", "wrap",
        "pudding", "beans", "lentil", "chickpea", "pizza", "chips", "fries",
        "cereal", "oat", "porridge", "cake", "biscuit", "pastry", "dessert",
    )
    low_priority_terms = (
        "beef", "chicken", "pork", "lamb", "fish", "egg", "cheese", "tofu",
        "broccoli", "carrot", "spinach", "lettuce", "cabbage", "courgette",
        "zucchini", "aubergine", "eggplant", "pepper", "mushroom", "tomato",
    )
    if any(term in item_l for term in carb_driver_terms):
        return 1.5
    if any(term in item_l for term in low_priority_terms):
        return 0.15
    return 1.0


def _clarification_target(evidence_items: list[dict]) -> tuple[dict | None, float, float]:
    """Pick the food whose uncertainty most affects meal carbs.

    Raw range spread alone can choose low-carb/protein foods when their candidate
    set includes noisy matches. Weighting by point-estimate carbs and generic
    carb-driver priority keeps the question clinically useful.
    """
    target = None
    max_spread = 0.0
    max_impact = 0.0
    for ev in evidence_items:
        cmin, cmax = ev.get("carb_range_g", (0.0, 0.0))
        food_spread = cmax - cmin
        carbs = float((ev.get("computed") or {}).get("carbs_g") or 0.0)
        item = (ev.get("parsed") or {}).get("item", "")
        impact = food_spread * max(carbs, 1.0) * _clarification_priority(item)
        if impact > max_impact:
            max_impact = impact
            max_spread = food_spread
            target = ev
    return target, max_spread, max_impact


def stage_decide_clarification(state: CompanionState) -> CompanionState:
    """Decide whether to ask a clarifying question based on uncertainty.

    Triggers a question when:
    - Meal is clinically significant (>= 40g carbs point estimate)
    - Meal-level range spread is large (>= 20g)
    - At least one food has high per-food spread (>= 15g), weighted toward carb impact
    """
    total_min, total_max = state.total_carbs_g_range
    spread = total_max - total_min

    most_uncertain, max_food_spread, max_impact = _clarification_target(state.evidence_items)

    # Trigger clarification when:
    # - Meal is clinically significant (>= 40g carbs)
    # - Meal-level range is wide (>= 20g spread)
    # - At least one food has meaningful carb uncertainty (>= 15g spread)
    # Note: target selection weights uncertainty by carb impact so low-carb
    # protein/veg items do not steal the clarification from potatoes, rice,
    # bread, pudding, beans, etc.
    if (
        state.totals.get("carbs_g", 0) >= 40.0
        and spread >= 20.0
        and most_uncertain is not None
        and max_food_spread >= 15.0
        and max_impact >= 150.0
    ):
        item = most_uncertain.get("parsed", {}).get("item", "this item")
        state.clarification_needed = True
        state.clarification_prompt = (
            f"For the {item}, is this more like a small, medium, or large portion?"
        )
    else:
        state.clarification_needed = False
        state.clarification_prompt = None

    return state


def stage_apply_clarification(state: CompanionState) -> CompanionState:
    """Adjust the most uncertain food's quantity based on user's clarification answer."""
    ans = (state.clarification_answer or "").lower().strip()
    if not ans:
        return state

    # Adjust the same clinically impactful food we'd ask about.
    most_uncertain_ev, _, _ = _clarification_target(state.evidence_items)
    if most_uncertain_ev is None:
        return state

    # Determine the quantity multiplier
    if "small" in ans or "little" in ans or "light" in ans:
        multiplier = 0.7
    elif "large" in ans or "big" in ans or "extra" in ans:
        multiplier = 1.3
    else:
        # "medium" or unrecognized → keep as-is
        return state

    # Apply to the evidence item
    parsed = most_uncertain_ev.get("parsed", {})
    old_q = float(parsed.get("quantity", 1.0) or 1.0)
    new_q = round(old_q * multiplier, 1)
    parsed["quantity"] = new_q
    most_uncertain_ev["parsed"] = parsed

    # Also update state.foods so that re-running stage_db_lookup picks up the change
    # state.foods may contain ParsedFood objects or dicts (after asdict)
    item_name = parsed.get("item", "").lower()
    for food in state.foods:
        if isinstance(food, dict):
            if food.get("item", "").lower() == item_name:
                food["quantity"] = new_q
                break
        else:
            if food.item.lower() == item_name:
                food.quantity = new_q
                break

    return state


async def stage_forecast(state: CompanionState) -> CompanionState:
    """Compute glucose forecast using ForecastStage."""
    forecast_stage = ForecastStage.from_profile(state.profile_config)
    forecast = forecast_stage.forecast(
        MealTotals.from_dict(state.totals),
        hour=19,
    )

    return CompanionState(
        **{**asdict(state), "forecast": forecast}
    )


async def stage_historical_context(state: CompanionState) -> CompanionState:
    """Look up similar meals from historical data.
    
    Uses the historical meal matcher to find past instances
    of similar meals and compute average glucose impact.
    """
    from app.services.historical_meal_matcher import summarize_similar_meals
    
    # Build food description for matching
    food_descriptions = [f.get("item", "unknown") if isinstance(f, dict) else f.item for f in state.foods]
    primary_food = food_descriptions[0] if food_descriptions else "unknown"
    
    # Look up historical context
    summary = summarize_similar_meals(
        query_description=f"{len(state.foods)} foods: {', '.join(food_descriptions)}",
        carbs_g=state.totals.get("carbs_g"),
        fat_g=state.totals.get("fat_g"),
        food_name=primary_food,
    )
    
    # Build historical timeline for graph visualization
    historical_timeline = build_historical_timeline(summary)
    
    return CompanionState(
        scenario=state.scenario,
        anchor_type=state.anchor_type,
        foods=state.foods,
        profile_config=state.profile_config,
        profile_json=state.profile_json,
        sim_reading=state.sim_reading,
        evidence_items=state.evidence_items,
        totals=state.totals,
        forecast=state.forecast,  # Preserve the forecast object
        similar_meals=[asdict(m) for m in summary.matched_meals],
        historical_timeline=historical_timeline,
        historical_summary={
            "matches_found": summary.matches_found,
            "avg_peak_delta_mgdl": summary.avg_peak_delta_mgdl,
            "avg_peak_time_minutes": summary.avg_peak_time_minutes,
            "narrative": summary.narrative,
            "confidence_tier": summary.confidence_tier,
        },
        question_mode=state.question_mode,
        safety_rule=state.safety_rule,
        total_carbs_g_range=state.total_carbs_g_range,
        confidence_overall=state.confidence_overall,
    )


async def stage_companion_advice(state: CompanionState, llm_call: Callable) -> CompanionState:
    """Generate companion response using evidence bundle."""
    from app.t1d_companion.local_loop import _load_prompt
    
    # Build risk flags
    risk_flags = []
    if state.totals.get("carbs_g", 0) >= 80:
        risk_flags.append("large_carb_load")
    if state.totals.get("fat_g", 0) >= 15:
        risk_flags.append("fat_may_extend_or_delay_rise")
    
    # Build bundle for LLM
    bundle = {
        "sim_user": {
            "label": state.profile_json.get("anchor_label"),
            "anchor_type": state.anchor_type,
            "description": state.profile_json.get("description"),
            "parameters": {
                "basal_glucose": round(state.profile_config.basal_glucose_mean),
                "carb_ratio": round(state.profile_config.carb_ratio, 1),
                "insulin_sensitivity": round(state.profile_config.insulin_sensitivity, 1),
                "fat_delay_hours": state.profile_config.fat_delay_hours,
                "exercise_drop_factor": state.profile_config.exercise_drop_factor,
            },
            "current_glucose": state.sim_reading.get("cgm_displayed_mg_dl"),
            "trend": state.sim_reading.get("trend"),
            "iob_units": state.sim_reading.get("insulin_on_board_units"),
        },
        "meal_totals": state.totals,
        "total_carbs_g_range": state.total_carbs_g_range,
        "confidence_overall": state.confidence_overall,
        "bolus_estimate": round(state.totals.get("carbs_g", 0) / state.profile_config.carb_ratio, 1),
        "risk_flags": risk_flags,
        "forecast": {
            "baseline": state.forecast.baseline_mg_dl,
            "peak": state.forecast.peak_mg_dl,
            "peak_time_min": state.forecast.peak_time_minutes,
            "forecast_points": [{"hour": p.hour, "glucose_mg_dl": p.glucose_mg_dl} for p in state.forecast.forecast_points] if state.forecast else [],
        } if state.forecast else {},
        "historical_context": state.historical_summary if hasattr(state, 'historical_summary') else {},
        "question_mode": state.question_mode,
        "safety_rule": state.safety_rule,
    }
    
    system = _load_prompt("companion_system.txt", "You are a warm T1D companion.")
    response = await llm_call([
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(bundle, indent=2)},
    ], 700)
    
    return CompanionState(
        scenario=state.scenario,
        anchor_type=state.anchor_type,
        foods=state.foods,
        profile_config=state.profile_config,
        profile_json=state.profile_json,
        sim_reading=state.sim_reading,
        evidence_items=state.evidence_items,
        totals=state.totals,
        forecast=state.forecast,
        similar_meals=state.similar_meals,
        historical_timeline=state.historical_timeline,
        historical_summary=state.historical_summary,
        response=response,
        question_mode=state.question_mode,
        safety_rule=state.safety_rule,
        total_carbs_g_range=state.total_carbs_g_range,
        confidence_overall=state.confidence_overall,
        llm_responses={**state.llm_responses, "advice": response, "bundle": json.dumps(bundle)},
    )


# ── Pipeline Runner (Factor 12) ──

async def run_companion_pipeline(
    scenario: str,
    anchor_type: str | None = None,
    model: str = "deepseek/deepseek-v4-flash",
    interactive: bool = False,
) -> CompanionState:
    """Run the full companion pipeline using the declarative stage graph.

    Each stage is a pure function that takes state and returns new state.
    This enables testing and replayability.
    """
    from sim_user_insights.scripts.pipeline import PipelineRunner
    from app.services.llm_call import LLMCapture, FirstCallLLMRouter
    from app.services.llm_service import LLMProvider

    # Detect question mode
    q_mode = "forecast"
    lower = scenario.lower()
    if "should i" in lower or "what should" in lower:
        q_mode = "action"
    elif "compare" in lower:
        q_mode = "compare"

    llm = FirstCallLLMRouter(
        first_call=LLMCapture(provider=LLMProvider.OLLAMA, model="llama3.1:latest"),
        remaining_calls=LLMCapture(provider=LLMProvider.OPENROUTER, model=model),
    )
    runner = PipelineRunner(llm=llm, interactive=interactive)
    result = await runner.run(
        scenario=scenario,
        anchor_type=anchor_type,
        question_mode=q_mode,
    )

    return result.state


# ── CLI Entry Point ──

async def main(verbose: bool = False, interactive: bool = False):
    import argparse

    parser = argparse.ArgumentParser(description="12-Factor T1D Companion Pipeline")
    parser.add_argument("scenario", nargs="*", default=[], help="Natural language scenario")
    parser.add_argument("--anchor", "-a", help="Anchor type (e.g., well_controlled, high_fat_delayed)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose stage output")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode with clarification questions")
    args = parser.parse_args()

    # Get scenario from CLI args or interactive prompt
    if args.interactive and not args.scenario:
        print("\n🥕 T1D Companion")
        print("─" * 40)
        scenario = input("What are you about to eat?\n> ").strip()
        if not scenario:
            print("No scenario provided. Exiting.")
            return
    else:
        scenario = " ".join(args.scenario)
    
    # First LLM call uses local Ollama; later calls use the configured provider.
    _cfg = get_settings()
    _provider = LLMProvider(_cfg.llm_provider)
    _model = _cfg.llm_model or "deepseek/deepseek-v4-flash"
    llm = FirstCallLLMRouter(
        first_call=LLMCapture(provider=LLMProvider.OLLAMA, model="llama3.1:latest"),
        remaining_calls=LLMCapture(provider=_provider, model=_model),
    )

    # Detect question mode
    q_mode = "forecast"
    if "should i" in scenario.lower() or "what should" in scenario.lower():
        q_mode = "action"
    elif "compare" in scenario.lower():
        q_mode = "compare"

    # Build and run pipeline
    from sim_user_insights.scripts.pipeline import PipelineRunner
    runner = PipelineRunner(llm=llm, interactive=args.interactive, verbose=args.verbose)

    if args.verbose:
        print("═"*70)
        print("VERBOSE PIPELINE TRACE - ALL INTERNAL OUTPUTS")
        print("═"*70)

    result = await runner.run(
        scenario=scenario,
        anchor_type=args.anchor,
        question_mode=q_mode,
    )

    # Handle interactive clarification
    if not result.completed and result.clarification_prompt:
        if args.verbose:
            print(f"\n[CLARIFICATION NEEDED] {result.clarification_prompt}")
        print(f"\n🤖 {result.clarification_prompt}")
        answer = input("> ").strip()
        result = await runner.resume_after_clarification(result.state, answer)

    state = result.state

    if args.verbose:
        print("\n" + "═"*70)
        print("FINAL OUTPUT")
        print("═"*70)

    print(f"\n╔══ SIM USER: {state.profile_json.get('anchor_label')} ({state.anchor_type}) ════════\n")
    print(f"CGM: {state.sim_reading.get('cgm_displayed_mg_dl')} mg/dL")
    print(f"\n{state.response}\n")
    
    # Show forecast graph with historical context
    if state.forecast:
        print(render_forecast(state.forecast, state.historical_timeline))
        if state.historical_summary and state.historical_summary.get("matches_found", 0) > 0:
            hs = state.historical_summary
            print(f"\n📊 Based on {hs.get('matches_found', 0)} similar meals in your history:")
            print(f"   {hs.get('narrative', '')}")


if __name__ == "__main__":
    import sys
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    interactive = "--interactive" in sys.argv or "-i" in sys.argv
    asyncio.run(main(verbose=verbose, interactive=interactive))