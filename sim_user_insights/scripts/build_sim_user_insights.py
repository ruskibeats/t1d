#!/usr/bin/env python3
"""Build deterministic insights from 90-day simulated T1D meal history.

This script intentionally keeps LLMs out of numeric analysis. It computes facts from
history rows and emits safe template-based plain-language insight drafts.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROFILE_CONFIGS = ROOT / "data" / "profile_configs.json"
HISTORY_PRIMARY = ROOT / "data" / "food_history_90d_enhanced.json"
HISTORY_FALLBACK = ROOT / "data" / "food_history_90d.json"
OUTPUT = ROOT / "sim_user_insights" / "outputs" / "sim_user_insights.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _nested(row: dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = row
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    idx = (len(values) - 1) * pct
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return round(values[lo], 1)
    return round(values[lo] * (hi - idx) + values[hi] * (idx - lo), 1)


def _summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "p25": None, "median": None, "mean": None, "p75": None, "max": None}
    return {
        "min": round(min(values), 1),
        "p25": _percentile(values, 0.25),
        "median": round(median(values), 1),
        "mean": round(mean(values), 1),
        "p75": _percentile(values, 0.75),
        "max": round(max(values), 1),
    }


def _date_range(rows: list[dict[str, Any]]) -> dict[str, str | None]:
    dates = []
    for row in rows:
        ts = row.get("timestamp")
        if not ts:
            continue
        try:
            dates.append(datetime.fromisoformat(str(ts)).date().isoformat())
        except ValueError:
            continue
    return {"start": min(dates) if dates else None, "end": max(dates) if dates else None}


def _bucket_peak(minutes: float) -> str:
    if minutes < 90:
        return "early_under_90_min"
    if minutes <= 150:
        return "typical_90_to_150_min"
    if minutes <= 240:
        return "delayed_150_to_240_min"
    return "very_delayed_over_240_min"


def _food_terms(food: str) -> list[str]:
    stop = {"and", "with", "the", "a", "an", "of", "combo", "meal", "plate", "standard"}
    return [t.lower().strip(" ,()-_") for t in food.split() if len(t.strip(" ,()-_")) > 2 and t.lower() not in stop]


def build_anchor_insights(anchor_type: str, profile: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    foods = [str(r.get("food") or "unknown") for r in rows]
    carbs = [_num(r.get("carb_estimate_g")) for r in rows]
    fats = [_num(r.get("fat_g")) for r in rows]
    peak_deltas = [_num(_nested(r, "cgm_impact.expected_peak_delta")) for r in rows]
    peak_minutes = [_num(_nested(r, "cgm_impact.peak_time_minutes")) for r in rows]
    fat_delay_hours = [_num(_nested(r, "cgm_impact.fat_delay_hours")) for r in rows]
    confidence = [_num(r.get("confidence_score")) for r in rows if r.get("confidence_score") is not None]

    high_carb_count = sum(1 for r in rows if bool(_nested(r, "safety_flags.high_carb", False)))
    high_fat_count = sum(1 for r in rows if bool(_nested(r, "safety_flags.high_fat", False)))
    delayed_risk_count = sum(1 for r in rows if bool(_nested(r, "safety_flags.delayed_risk", False)))
    peak_buckets = Counter(_bucket_peak(v) for v in peak_minutes if v > 0)
    term_counts = Counter(term for food in foods for term in _food_terms(food))

    meal_count = len(rows)
    delayed_rate = delayed_risk_count / meal_count if meal_count else 0
    high_fat_rate = high_fat_count / meal_count if meal_count else 0
    high_carb_rate = high_carb_count / meal_count if meal_count else 0

    top_foods = [{"food": food, "count": count} for food, count in Counter(foods).most_common(10)]
    common_terms = [{"term": term, "count": count} for term, count in term_counts.most_common(20)]

    patterns: list[dict[str, Any]] = []
    if delayed_rate >= 0.25 or median(fat_delay_hours or [0]) >= 2.0:
        patterns.append({
            "id": "delayed_rise_tendency",
            "title": "Delayed-rise tendency",
            "evidence": {
                "matching_meals": delayed_risk_count,
                "meal_count": meal_count,
                "rate": round(delayed_rate, 3),
                "median_peak_minutes": round(median(peak_minutes), 1) if peak_minutes else None,
                "median_fat_delay_hours": round(median(fat_delay_hours), 1) if fat_delay_hours else None,
            },
            "plain_language": "This simulated profile often shows later glucose movement after meals in its history, so timing matters as much as the first rise.",
        })
    if high_carb_rate >= 0.35:
        patterns.append({
            "id": "frequent_high_carb_meals",
            "title": "Frequent high-carb meals",
            "evidence": {"matching_meals": high_carb_count, "meal_count": meal_count, "rate": round(high_carb_rate, 3)},
            "plain_language": "A sizeable share of this simulated profile's history involves higher-carb meals, which makes post-meal monitoring especially relevant.",
        })
    if high_fat_rate >= 0.20:
        patterns.append({
            "id": "higher_fat_context",
            "title": "Higher-fat meal context",
            "evidence": {"matching_meals": high_fat_count, "meal_count": meal_count, "rate": round(high_fat_rate, 3)},
            "plain_language": "Higher-fat meals appear often enough in this simulated history to treat delayed or prolonged glucose effects as a known uncertainty.",
        })

    return {
        "anchor_type": anchor_type,
        "profile": profile,
        "history": {
            "meal_count": meal_count,
            "date_range": _date_range(rows),
            "top_foods": top_foods,
            "common_food_terms": common_terms,
        },
        "distributions": {
            "carbs_g": _summary(carbs),
            "fat_g": _summary(fats),
            "expected_peak_delta_mg_dl": _summary(peak_deltas),
            "peak_time_minutes": _summary(peak_minutes),
            "fat_delay_hours": _summary(fat_delay_hours),
            "confidence_score": _summary(confidence),
        },
        "rates": {
            "high_carb": round(high_carb_rate, 3),
            "high_fat": round(high_fat_rate, 3),
            "delayed_risk": round(delayed_rate, 3),
        },
        "peak_timing_buckets": dict(peak_buckets),
        "patterns": patterns,
        "safety_notes": [
            "Historical bolus/prebolus fields are simulator artifacts and must not be phrased as instructions.",
            "Use as educational simulated-profile context only.",
        ],
    }


def main() -> None:
    profiles = _load_json(PROFILE_CONFIGS)
    history_path = HISTORY_PRIMARY if HISTORY_PRIMARY.exists() else HISTORY_FALLBACK
    rows = _load_json(history_path)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        anchor = row.get("anchor_type")
        if anchor:
            grouped[str(anchor)].append(row)

    anchors = []
    for anchor_type in sorted(profiles):
        anchors.append(build_anchor_insights(anchor_type, profiles[anchor_type], grouped.get(anchor_type, [])))

    output = {
        "schema_version": "sim_user_insights.v1",
        "source_history": str(history_path.relative_to(ROOT)),
        "source_profiles": str(PROFILE_CONFIGS.relative_to(ROOT)),
        "anchor_count": len(anchors),
        "total_history_rows": len(rows),
        "anchors": anchors,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2))
    print(f"Wrote {OUTPUT} ({len(anchors)} anchors, {len(rows)} history rows)")


if __name__ == "__main__":
    main()
