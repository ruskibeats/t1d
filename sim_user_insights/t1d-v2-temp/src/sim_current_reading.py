#!/usr/bin/env python3
"""Generate a simulated current CGM reading for a given anchor/profile.

Returns: current glucose (with 15-min sensor lag), trend arrow, context bundle.
"""

from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_PATH = Path("/root/t1d/data/food_history_90d_enhanced.json")


def _num(val: Any, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _soft_glucose_cap(v: float) -> float:
    """Soft physiological CGM boundary matching the simulator engine."""
    if v > 400.0:
        return 400.0 + 15.0 * (1.0 - math.exp(-(v - 400.0) / 15.0))
    if v < 40.0:
        return 40.0 - 15.0 * (1.0 - math.exp(-(40.0 - v) / 15.0))
    return v


def generate_current_reading(
    anchor: str,
    config: Any,
    current_hour: int = 19,
    seed: int | None = None,
) -> dict[str, Any]:
    """Generate a plausible current CGM reading for a sim user.

    Args:
        anchor: Anchor type string (e.g. "high_fat_delayed").
        config: PatientConfig with basal_glucose_mean, variability_cv, etc.
        current_hour: Hour of day (0-23) for the simulated reading.
        seed: Optional RNG seed for reproducibility.

    Returns:
        Dict with current_glucose, true_glucose, trend, sensor_lag_min,
        insulin_on_board, and recent_history context.
    """
    rng = random.Random(seed)
    basal = _num(getattr(config, "basal_glucose_mean", 110))
    cv = _num(getattr(config, "variability_cv", 25))
    dawn_strength = _num(getattr(config, "dawn_effect_strength", 10))
    hypo_risk = _num(getattr(config, "hypo_risk", 0.05))
    noise_sd = _num(getattr(config, "noise_sd", 8))

    # ── True glucose at this hour ──
    # Apply dawn effect (higher in early morning)
    dawn_bump = 0
    if 5 <= current_hour <= 9:
        dawn_bump = dawn_strength * 0.3 * rng.uniform(0.5, 1.0)

    # Apply diurnal variation (typically slightly lower in afternoon, higher evening)
    diurnal = {
        0: -5, 1: -8, 2: -10, 3: -10, 4: -8, 5: -3,
        6: 0, 7: 5, 8: 10, 9: 8, 10: 5, 11: 3,
        12: 0, 13: -2, 14: -3, 15: -2, 16: 0, 17: 3,
        18: 5, 19: 8, 20: 10, 21: 8, 22: 3, 23: -2,
    }
    hourly_offset = diurnal.get(current_hour, 0)

    # Random variability
    variability = rng.gauss(0, basal * cv / 100 * 0.3)

    true_glucose = basal + dawn_bump + hourly_offset + variability
    true_glucose = _soft_glucose_cap(true_glucose)

    # ── Trend direction from recent CGM trajectory ──
    # Simulate a short trace to determine trend
    trace: list[float] = []
    for step in range(6):  # 6 steps × 5 min = 30 min of history
        t = 30 - step * 5
        noise = rng.gauss(0, noise_sd * 0.3)
        trace.append(true_glucose + noise - t * 0.1 * rng.uniform(-0.5, 0.5))

    # Fit: is it rising or falling?
    recent_5 = trace[-1]  # 5 min ago
    recent_15 = trace[-3] if len(trace) >= 3 else trace[-1]  # 15 min ago
    delta_10min = recent_5 - recent_15  # change over 10 min

    if delta_10min > 2:
        trend = "rising"
    elif delta_10min < -2:
        trend = "falling"
    else:
        trend = "steady"

    trend_arrow = {"rising": "↑", "falling": "↓", "steady": "→"}[trend]

    # ── CGM sensor lag (15 min behind true) ──
    # If rising, CGM reads lower than true; if falling, reads higher
    lag_minutes = 15
    if trend == "rising":
        # True glucose is climbing; CGM trails behind
        sensor_lag_mg_dl = -delta_10min * 1.5  # ~3 mg/dL for 2 mg/dL/10min rise
    elif trend == "falling":
        sensor_lag_mg_dl = abs(delta_10min) * 1.5
    else:
        sensor_lag_mg_dl = rng.gauss(0, 2)

    current_glucose = round(_soft_glucose_cap(true_glucose + sensor_lag_mg_dl), 0)

    # ── Insulin on board ──
    # Check if there was a recent meal in the 90-day history around this time
    iob = 0.0
    recent_meal_time = None
    recent_meal_name = None
    if HISTORY_PATH.exists():
        try:
            records = json.loads(HISTORY_PATH.read_text())
            # Find most recent meal within 2-4 hours before current time
            for r in records:
                if r.get("anchor_type") != anchor:
                    continue
                ts = str(r.get("timestamp", ""))
                try:
                    meal_hour = int(ts.split("T")[1].split(":")[0])
                except (IndexError, ValueError):
                    continue
                # Meal was 2-4 hours before current time
                hours_ago = (current_hour - meal_hour) % 24
                if 1 <= hours_ago <= 4:
                    meal_carbs = _num(r.get("carb_estimate_g"))
                    carb_ratio = _num(getattr(config, "carb_ratio", 15))
                    if carb_ratio > 0 and meal_carbs > 0:
                        iob = meal_carbs / carb_ratio * max(0, 1 - hours_ago / 5)
                        recent_meal_name = str(r.get("food", ""))
                        recent_meal_time = ts
                    break
        except Exception:
            pass

    # ── Build context bundle ──
    return {
        "anchor": anchor,
        "current_hour": current_hour,
        "true_glucose_mg_dl": round(true_glucose, 0),
        "cgm_displayed_mg_dl": current_glucose,
        "sensor_lag_minutes": lag_minutes,
        "trend": trend,
        "trend_arrow": trend_arrow,
        "basal_mg_dl": round(basal, 0),
        "dawn_bump_mg_dl": round(dawn_bump, 0),
        "hourly_offset_mg_dl": hourly_offset,
        "variability_mg_dl": round(variability, 0),
        "insulin_on_board_units": round(iob, 2),
        "recent_meal": recent_meal_name,
        "recent_meal_time": recent_meal_time,
        "recent_trace_mg_dl": [round(v, 0) for v in trace[-5:]],
        "context_summary": (
            f"Current CGM: {current_glucose} mg/dL {trend_arrow} "
            f"(sensor 15 min lag, true ~{round(true_glucose, 0)}). "
            f"Basal: {basal}. IOB: {iob:.1f}u"
            + (f" from {recent_meal_name}" if recent_meal_name else "")
            + f" | Hour: {current_hour}:00. {anchor} profile."
        ),
    }