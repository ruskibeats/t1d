#!/usr/bin/env python3
"""Staged T1D Companion — LLM reasons, code calculates, together they advise.

Pipeline:
  Stage 1 — LLM interprets raw scenario → food items
  Stage 2 — LLM normalises quantities + units
  Stage 3 — Code searches OpenFoodFacts Postgres
  Stage 4 — LLM picks best match from candidates
  Stage 5 — Code computes totals + forecast + history
  Stage 6 — LLM generates companion advice
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import random as rand
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import median
from typing import Any

_env = Path("/root/t1d/.env")
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.core.database import db_manager, get_settings
from app.food.service import FoodService
from app.services.llm_service import LLMProvider, LLMService
from app.t1d_companion.local_loop import (
    _extract_json,
    _load_prompt,
    _normalise_food_dict,
    calculate_food_evidence,
    fallback_parse_scenario,
    pick_profile_by_anchor,
    search_food_candidates,
)
from app.simulator.schemas import AnchorType
from sim_user_insights.scripts.sim_current_reading import generate_current_reading
from sim_user_insights.scripts.forecast_engine import forecast_glucose, MealTotals

# ── Config ──
MODEL = "deepseek/deepseek-v4-flash"
ANCHOR = None  # None = random
MEAL_TIME = "19:00"
SCENARIO = "6 chicken wings breadcrumb coating pot of coleslaw"


# ── 12-Factor State Management (Factor 5: Unify execution state and business state) ──

@dataclass
class CompanionState:
    """Unified execution and business state.
    
    Captures everything needed to pause/resume or replay the pipeline.
    Enables stateless reducer pattern (Factor 12).
    """
    scenario: str
    anchor_type: str | None = None
    foods: list = field(default_factory=list)
    profile_config: Any = None
    profile_json: dict = field(default_factory=dict)
    sim_reading: dict = field(default_factory=dict)
    evidence_items: list = field(default_factory=list)
    serving_sizes: dict = field(default_factory=dict)
    totals: dict = field(default_factory=dict)
    forecast: Any = None
    similar_meals: list = field(default_factory=list)
    llm_review: dict = field(default_factory=dict)
    companion_response: str = ""
    question_mode: str = "forecast"
    safety_rule: str = ""
    raw_llm_responses: dict = field(default_factory=dict)
    
    def to_context(self) -> dict[str, Any]:
        """Build context window content for LLM stages (Factor 3: Own your context window)."""
        return {
            "scenario": self.scenario,
            "anchor_type": self.anchor_type,
            "foods": [asdict(f) if hasattr(f, '__dataclass_fields__') else f for f in self.foods],
            "profile": self.profile_json,
            "current_glucose": self.sim_reading.get("cgm_displayed_mg_dl"),
            "totals": self.totals,
            "forecast": asdict(self.forecast) if self.forecast and hasattr(self.forecast, '__dataclass_fields__') else self.forecast,
        }


# ── Pipeline Stage Functions (Factor 8: Own your control flow) ──


# ── Helpers ──

def _num(val: Any, default: float = 0.0) -> float:
    try:
        if val is None: return default
        return float(val)
    except (TypeError, ValueError):
        return default


async def call_model(messages, max_tokens=600):
    llm = LLMService(provider=LLMProvider.OPENROUTER, model=MODEL)
    result = await llm._call_llm(messages, max_tokens=max_tokens, stream=False)
    return result["response"] if result else None


def show_prompt(stage: str, messages: list[dict]) -> None:
    """Print the system + user prompt for a stage."""
    print(f"\n  ── Prompt sent to {MODEL} [{stage}] ──")
    for msg in messages:
        role = msg["role"].upper()
        content = msg["content"]
        # Truncate long content
        if len(content) > 600:
            content = content[:600] + "... [truncated]"
        for line in content.split("\n"):
            print(f"  [{role}] {line}")
    print(f"  ── End prompt ──")


def section(title: str, char: str = "═") -> None:
    print(f"\n╔══ {title} ═{'═' * (60 - len(title))}╗")


# ── Question templates ──

QUESTION_TEMPLATES = {
    "forecast": {
        "patterns": ["what will likely happen", "what will happen", "what happens"],
        "focus": "Forecast timing and glucose impact",
        "safety": "Educational simulation only. Never give dosing instructions.",
    },
    "action": {
        "patterns": ["what should i do", "what do i do", "should i"],
        "focus": "Monitoring advice and risk awareness. NEVER dosing advice.",
        "safety": "CRITICAL: User asked what to do. Only monitoring timing, CGM checks.",
    },
    "compare": {
        "patterns": ["compare", "instead of", "vs", "versus"],
        "focus": "Compare food choices and glucose impact differences",
        "safety": "Educational comparison only. No dosing advice.",
    },
    "risk": {
        "patterns": ["is this safe", "is it safe", "dangerous", "risky"],
        "focus": "Risk assessment: carb load, fat delay, alcohol, hypo risk",
        "safety": "Emphasise uncertainty. Flag risks without alarming.",
    },
    "redirect": {
        "patterns": ["how much", "how many units", "dose", "bolus"],
        "focus": "Redirect to educational estimate. Never frame as recommendation.",
        "safety": "CRITICAL: Dosing ask. Use 'educational estimate'. Never 'take X units'.",
    },
}


def detect_question_mode(scenario: str) -> tuple[str, dict]:
    lower = scenario.lower()
    for mode, t in QUESTION_TEMPLATES.items():
        for pat in t["patterns"]:
            if pat in lower:
                return mode, t
    return "forecast", QUESTION_TEMPLATES["forecast"]


# ── Forecast engine ──

# ── History matching ──

def find_enriched_similar(foods, anchor: str, limit: int = 5):
    path = Path("/root/t1d/data/food_history_90d_enhanced.json")
    if not path.exists(): return []
    try:
        records = json.loads(path.read_text())
    except Exception:
        return []
    terms = set()
    for f in foods:
        terms.add(f.item.lower())
        for t in f.item.lower().split():
            t = t.strip(" ,-()")
            if len(t) > 2: terms.add(t)
    scored = []
    for r in records:
        if r.get("anchor_type") != anchor: continue
        fn = str(r.get("food", "")).lower()
        s = sum(2 for qt in terms if qt in fn)
        if s > 0: scored.append((s, r))
    scored.sort(key=lambda x: -x[0])
    seen, deduped = set(), []
    for _s, rec in scored:
        fn = str(rec.get("food", "")).lower()
        if fn not in seen:
            seen.add(fn)
            deduped.append(rec)
    return deduped[:limit]


# ── Main pipeline ──

async def main():
    q_mode, q_template = detect_question_mode(SCENARIO)

    # ── Stage 0: Pick sim user ──
    section("STAGE 0 — SIM USER SELECTION")
    if ANCHOR is None:
        random_anchor = rand.choice(list(AnchorType))
        config, profile_json = pick_profile_by_anchor(random_anchor)
    else:
        config, profile_json = pick_profile_by_anchor(ANCHOR)
    anchor_str = config.anchor_type.value

    sim_reading = generate_current_reading(anchor_str, config, current_hour=19)
    print(f"  Profile: {profile_json.get('anchor_label')} ({anchor_str})")
    print(f"  CGM: {sim_reading['cgm_displayed_mg_dl']} mg/dL {sim_reading['trend_arrow']}  |  "
          f"IOB: {sim_reading['insulin_on_board_units']}u  |  Basal: {sim_reading['basal_mg_dl']}")
    print(f"  {profile_json.get('description')}")

    # ── Stage 1: LLM interprets scenario → food items ──
    section("STAGE 1 — LLM INTERPRETS SCENARIO")
    print(f"  Raw input: \"{SCENARIO}\"")
    show_prompt("Stage 1 — parse foods", [
        {"role": "system", "content": _load_prompt("parser_system.txt", "Return JSON")},
        {"role": "user", "content": SCENARIO},
    ])
    raw = await call_model([
        {"role": "system", "content": _load_prompt("parser_system.txt", "Return JSON")},
        {"role": "user", "content": SCENARIO},
    ], 300)

    foods = fallback_parse_scenario(SCENARIO)  # fallback baseline
    llm_narrative = ""
    if raw:
        try:
            data = _extract_json(raw)
            llm_items = data if isinstance(data, list) else data.get("foods", [])
            llm_foods = [_normalise_food_dict(x) for x in llm_items]
            if len(llm_foods) >= len(foods):
                foods = llm_foods
                # Build narrative
                descs = [f"{f.quantity} {f.unit or ''} {f.item}" for f in foods]
                llm_narrative = f"  I see: {', '.join(descs)}"
        except Exception:
            pass

    fallback_ref = fallback_parse_scenario(SCENARIO)
    if len(fallback_ref) > len(foods):
        foods = fallback_ref

    descs = [f"{f.quantity} {f.unit or ''} {f.item}" for f in foods]
    print(f"  → Parsed: {', '.join(descs)}")
    if not llm_narrative:
        print(f"  (fallback parser active)")

    # Clean garbled food names using LLM
    raw_names = [f.item for f in foods]
    clean_prompt = (
        "Clean these food names — remove punctuation, trailing context, percentages, descriptors. "
        "Return ONLY a JSON array of strings in the same order.\n"
        f"Input: {json.dumps(raw_names)}"
    )
    show_prompt("Stage 1.5 — clean names", [
        {"role": "system", "content": _load_prompt("clean_names.txt", "Return ONLY a JSON array of strings.")},
        {"role": "user", "content": clean_prompt},
    ])
    cleaned_raw = await call_model([
        {"role": "system", "content": _load_prompt("clean_names.txt", "Return ONLY a JSON array of strings.")},
        {"role": "user", "content": clean_prompt},
    ], 200)
    if cleaned_raw:
        try:
            cleaned = json.loads(cleaned_raw.strip())
            if isinstance(cleaned, list) and len(cleaned) == len(foods):
                for i, name in enumerate(cleaned):
                    if name and isinstance(name, str) and len(name) > 1:
                        foods[i].item = name.strip().lower()
        except Exception:
            pass

    cleaned_descs = [f"{f.quantity} {f.unit or ''} {f.item}" for f in foods]
    print(f"  → Cleaned: {', '.join(cleaned_descs)}")

    # ── Stage 2: LLM normalises quantities and units ──
    section("STAGE 2 — LLM NORMALISES PORTIONS")
    norm_prompt = (
        "For each food item, estimate the weight in grams based on typical portions. "
        "Return ONLY a JSON array of numbers in the same order.\n"
        f"Items: {json.dumps([{'item': f.item, 'quantity': f.quantity, 'unit': f.unit} for f in foods])}\n"
        "Rules: 1 chicken wing ≈ 50g. 1 pot coleslaw ≈ 200g. "
        "1 pint beer ≈ 568ml. 1 slice pizza ≈ 100g. Default to 100g if unknown."
    )
    show_prompt("Stage 2 — normalise portions", [
        {"role": "system", "content": _load_prompt("normalise_portions.txt", "Return ONLY a JSON array of numbers. No explanation.")},
        {"role": "user", "content": norm_prompt},
    ])
    norm_raw = await call_model([
        {"role": "system", "content": _load_prompt("normalise_portions.txt", "Return ONLY a JSON array of numbers. No explanation.")},
        {"role": "user", "content": norm_prompt},
    ], 200)

    serving_sizes = [100] * len(foods)  # default
    if norm_raw:
        try:
            parsed = json.loads(norm_raw.strip())
            if isinstance(parsed, list) and len(parsed) == len(foods):
                serving_sizes = [max(10, min(2000, float(v))) for v in parsed]
        except Exception:
            pass

    for i, f in enumerate(foods):
        old = f.quantity
        # serving_sizes[i] is total estimated grams for the whole portion
        if f.unit not in ("ml", "g"):
            f.quantity = serving_sizes[i]
            f.unit = "g"
        print(f"  {old} {f.unit or ''} {f.item} → {round(f.quantity, 0)}g total")

    # ── Stage 3: Code searches OpenFoodFacts ──
    section("STAGE 3 — DATABASE LOOKUP (OpenFoodFacts)")
    settings = get_settings()
    db_manager.init_db(settings.database_url)
    evidence_items = []
    async with db_manager.get_session() as session:
        service = FoodService(session)
        for i, food in enumerate(foods):
            candidates = await search_food_candidates(service, food)
            evidence = calculate_food_evidence(food, candidates)
            evidence_items.append(evidence)
            match = evidence.selected_match
            if match:
                print(f"  {round(food.quantity, 0)}g {food.item} → {match.get('name')} [{match.get('brand') or '?'}]")
                print(f"    {evidence.computed or 'no match'}")
            else:
                print(f"  {food.item} → no DB match")

    totals = {"carbs_g": 0.0, "fat_g": 0.0, "sugars_g": 0.0, "protein_g": 0.0, "kcal": 0.0}
    for item in evidence_items:
        if item.computed:
            for k in totals:
                totals[k] += item.computed.get(k, 0.0)
    totals = {k: round(v, 1) for k, v in totals.items()}
    print(f"  ─────────────────────────────────────")
    print(f"  TOTALS: {totals['carbs_g']}g carbs, {totals['fat_g']}g fat, {totals['protein_g']}g protein, {totals['kcal']} kcal")

    # ── Stage 4: LLM picks best match + flags uncertainty ──
    section("STAGE 4 — LLM REVIEWS MATCHES")
    match_summary = []
    for i, (food, ev) in enumerate(zip(foods, evidence_items)):
        m = ev.selected_match
        if m:
            match_summary.append(f"  {food.item}: {m.get('name')} [{m.get('brand') or '?'}] conf={ev.confidence}")
        else:
            match_summary.append(f"  {food.item}: no match — flagging uncertainty")

    show_prompt("Stage 4 — review matches", [
        {"role": "system", "content": _load_prompt("review_matches.txt", "You review food database matches for accuracy. Return ONLY JSON.")},
        {"role": "user", "content": json.dumps({
            "foods": [{"item": f.item, "quantity": round(f.quantity), "unit": f.unit} for f in foods],
            "matches": match_summary,
            "totals": totals,
        }, indent=2)},
    ])
    match_raw = await call_model([
        {"role": "system", "content": _load_prompt("review_matches.txt", "You review food database matches for accuracy. Return ONLY JSON.")},
        {"role": "user", "content": json.dumps({
            "foods": [{"item": f.item, "quantity": round(f.quantity), "unit": f.unit} for f in foods],
            "matches": match_summary,
            "totals": totals,
        }, indent=2)},
    ], 400)

    llm_review = {}
    if match_raw:
        try:
            llm_review = _extract_json(match_raw)
            if isinstance(llm_review, dict):
                print(f"  LLM confidence: {llm_review.get('confidence', 'medium')}")
                for c in llm_review.get("concerns", []):
                    print(f"  ⚠ {c}")
        except Exception:
            print(f"  No review generated")
    if not llm_review:
        print(f"  Auto-accepted DB matches (no LLM review)")

    # ── Stage 5: Code computes forecast + history ──
    section("STAGE 5 — CODE: FORECAST + HISTORY")
    forecast = forecast_glucose(
        MealTotals.from_dict(totals),
        basal_mg_dl=_num(getattr(config, "basal_glucose_mean", 110)),
        carb_ratio=_num(getattr(config, "carb_ratio", 15)),
        insulin_sensitivity=_num(getattr(config, "insulin_sensitivity", 35)),
        fat_delay_hours=_num(getattr(config, "fat_delay_hours", 3.0)),
        exercise_drop_factor=_num(getattr(config, "exercise_drop_factor", 1.0)),
        anchor_type=anchor_str,
        hour=19,
    )
    similar = find_enriched_similar(foods, anchor_str)

    print(f"  Glucose forecast:")
    print(f"    Baseline: {forecast.baseline_mg_dl} mg/dL")
    print(f"    Peak: {forecast.peak_mg_dl} mg/dL @ ~{forecast.peak_time_minutes} min")
    for pt in forecast.forecast_points:
        bar = "█" * max(1, int(pt.glucose_mg_dl / 10))
        print(f"    {pt.hour}h: {pt.glucose_mg_dl:3.0f} mg/dL {bar}")

    if similar:
        print(f"\n  Historical matches:")
        agg_peak = median([s.get("cgm_impact", {}).get("expected_peak_delta", 0) for s in similar if s.get("cgm_impact")])
        agg_time = median([s.get("cgm_impact", {}).get("peak_time_minutes", 0) for s in similar if s.get("cgm_impact")])
        print(f"    Median: peak +{agg_peak:.0f} mg/dL @ {agg_time:.0f} min")
        for s in similar[:4]:
            print(f"    • {s.get('food')}: {s.get('carb_estimate_g')}g carbs → +{s.get('cgm_impact',{}).get('expected_peak_delta')} mg/dL @ {s.get('cgm_impact',{}).get('peak_time_minutes')}min")

    print(f"\n  Nighttime:")
    for nt in forecast.nighttime:
        print(f"    {nt.time}: {nt.glucose_mg_dl} mg/dL — {nt.note}")

    # ── Stage 6: LLM generates companion advice ──
    section("STAGE 6 — COMPANION ADVICE")
    risk_flags = []
    if totals["carbs_g"] >= 80: risk_flags.append("large_carb_load")
    if totals["fat_g"] >= 15: risk_flags.append("fat_may_extend_or_delay_rise")
    if config.exercise_drop_factor >= 3: risk_flags.append("exercise_sensitive_profile")

    bundle = {
        "sim_user": {
            "label": profile_json.get("anchor_label"),
            "anchor_type": anchor_str,
            "description": profile_json.get("description"),
            "parameters": {
                "basal_glucose": round(config.basal_glucose_mean),
                "carb_ratio": round(config.carb_ratio, 1),
                "insulin_sensitivity": round(config.insulin_sensitivity, 1),
                "fat_delay_hours": config.fat_delay_hours,
                "exercise_drop_factor": config.exercise_drop_factor,
            },
            "current_glucose": sim_reading["cgm_displayed_mg_dl"],
            "trend": sim_reading["trend"],
            "iob_units": sim_reading["insulin_on_board_units"],
        },
        "meal_totals": totals,
        "bolus_estimate": round(totals["carbs_g"] / config.carb_ratio, 1),
        "risk_flags": risk_flags,
        "forecast": {
            "baseline": forecast.baseline_mg_dl,
            "peak": forecast.peak_mg_dl,
            "peak_time_min": forecast.peak_time_minutes,
            "exercise_heat_modifier": forecast.exercise_heat_modifier,
            "nighttime": [{"time": n.time, "glucose_mg_dl": n.glucose_mg_dl, "note": n.note} for n in forecast.nighttime],
        },
        "history": [{"food": s.get("food"), "carbs": s.get("carb_estimate_g"),
                     "peak_delta": s.get("cgm_impact", {}).get("expected_peak_delta"),
                     "peak_time": s.get("cgm_impact", {}).get("peak_time_minutes")}
                    for s in similar[:4]],
        "question_mode": q_mode,
        "safety_rule": q_template["safety"],
    }

    system = _load_prompt("companion_system.txt",
        "You are a warm T1D companion. Use ONLY the JSON evidence. "
        "Never say 'take X units' or 'split bolus'. "
        "Say 'educational estimate for this simulated profile'. "
        f"\nQuestion mode: {q_mode}. Focus: {q_template['focus']}. "
        f"Safety: {q_template['safety']}")

    show_prompt("Stage 6 — companion advice", [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(bundle, indent=2)},
    ])
    response = await call_model([
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(bundle, indent=2)},
    ], 700)

    print(f"  {response or '[No response]'}")

    # Safety filter
    forbidden = [r"(?i)(take|give|administer)\s+.*\d+\.?\d*\s*units", r"(?i)split bolus", r"(?i)recommended bolus"]
    violations = [p for p in forbidden if response and re.search(p, response)]
    print(f"\n╔══ SAFETY ═══════════════════════════════════════════════════╗")
    print(f"  {'✅ Passed' if not violations else '⚠️  FLAGGED: ' + '; '.join(violations)}")


if __name__ == "__main__":
    asyncio.run(main())
