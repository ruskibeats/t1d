#!/usr/bin/env python3
"""Calibration harness for T1D Companion forecasts.

Compare predictions against real CGM history (Nightscout CSV exports, Dexcom API).
Focus on peak rise, time-to-peak, and fat/protein delay detection.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import statistics


@dataclass
class CGMEpoch:
    """Single CGM reading with metadata."""
    timestamp: str
    glucose_mg_dl: int
    source: str = "nightscout"


@dataclass  
class MealTrace:
    """Meal event with before/after glucose context."""
    meal_time: str
    carbs_g: float
    fat_g: float | None = None
    protein_g: float | None = None
    glucose_before: int | None = None
    glucose_after_peak: int | None = None
    peak_time_offset_min: int | None = None
    peak_glucose: int | None = None


def load_nightscout_csv(csv_path: Path) -> list[CGMEpoch]:
    """Load Nightscout glucose data from CSV export.
    
    Expected columns: 'date', 'sgv' (or 'glucose'), optionally 'type'
    Returns sorted list of CGMEpoch objects.
    """
    epochs = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            glucose = int(row.get('sgv') or row.get('glucose') or 0)
            if glucose:
                epochs.append(CGMEpoch(
                    timestamp=row.get('date', row.get('timestamp', '')),
                    glucose_mg_dl=glucose,
                ))
    return sorted(epochs, key=lambda e: e.timestamp)


def load_nightscout_json(json_path: Path) -> list[CGMEpoch]:
    """Load Nightscout glucose data from JSON API export.
    
    Each entry has: dateString, sgv fields.
    Returns sorted list of CGMEpoch objects.
    """
    import json
    with open(json_path) as f:
        entries = json.load(f)
    
    epochs = []
    for entry in entries:
        if entry.get('sgv'):
            epochs.append(CGMEpoch(
                timestamp=entry.get('dateString', entry.get('created_at', '')),
                glucose_mg_dl=entry['sgv'],
            ))
    return sorted(epochs, key=lambda e: e.timestamp)


def fetch_nightscout_entries(base_url: str, count: int = 1000) -> list[CGMEpoch]:
    """Fetch entries directly from Nightscout API.
    
    Args:
        base_url: Nightscout base URL (e.g., http://192.168.0.150:1337)
        count: Number of entries to fetch
        
    Returns:
        Sorted CGMEpoch list
    """
    import urllib.request, json
    
    url = f"{base_url.rstrip('/')}/api/v1/entries/sgv.json?count={count}"
    with urllib.request.urlopen(url) as response:
        entries = json.loads(response.read())
    
    epochs = []
    for entry in entries:
        if entry.get('sgv'):
            epochs.append(CGMEpoch(
                timestamp=entry.get('dateString', ''),
                glucose_mg_dl=entry['sgv'],
            ))
    return sorted(epochs, key=lambda e: e.timestamp)


def find_meal_events(
    epochs: list[CGMEpoch],
    treatments_path: Path | None = None,
    carbs_threshold: int = 30,
) -> list[MealTrace]:
    """Identify meal events from glucose patterns.
    
    Heuristic: Look for >30g carb equivalents where glucose rises >20 mg/dL
    from pre-meal baseline within 60-180 minutes.
    """
    meals = []
    
    # Simple heuristic: find rapid rises
    for i in range(5, len(epochs) - 12):
        pre_slice = epochs[i-5:i]
        post_slice = epochs[i:i+12]  # 1 hour
        
        pre_bg = statistics.mean(e.glucose_mg_dl for e in pre_slice)
        post_bg = max(e.glucose_mg_dl for e in post_slice)
        rise = post_bg - pre_bg
        
        # Estimate carbs from rise (back-of-envelope)
        if rise > 20:
            carbs_est = max(30, int(rise / 2.5))  # Rough ratio
            peak_idx = i + post_slice.index(max(post_slice, key=lambda e: e.glucose_mg_dl))
            
            meals.append(MealTrace(
                meal_time=epochs[i].timestamp,
                carbs_g=float(carbs_est),
                glucose_before=int(round(pre_bg)),
                peak_glucose=int(round(post_bg)),
                peak_time_offset_min=peak_idx * 5,
            ))
    
    return meals


def compare_forecast_to_trace(
    forecast_result: Any,
    meal_trace: MealTrace,
) -> dict[str, float | int | str]:
    """Compare ForecastResult predictions against a real meal trace.
    
    Returns error metrics for calibration.
    """
    predicted_peak = forecast_result.peak_mg_dl
    predicted_time = forecast_result.peak_time_minutes
    
    actual_peak = meal_trace.peak_glucose or 0
    actual_time = meal_trace.peak_time_offset_min or 0
    
    peak_error = abs(predicted_peak - actual_peak) if actual_peak else 0
    time_error = abs(predicted_time - actual_time) if actual_time else 0
    
    return {
        "predicted_peak": predicted_peak,
        "actual_peak": actual_peak,
        "peak_error_mgdl": peak_error,
        "predicted_time_min": predicted_time,
        "actual_time_min": actual_time,
        "time_error_min": time_error,
        "carb_estimate": meal_trace.carbs_g,
        "calibration_status": (
            "good" if peak_error <= 30 and time_error <= 60 else
            "warning" if peak_error <= 60 and time_error <= 120 else
            "poor"
        ),
    }


def run_calibration_suite(
    forecast_func,
    meals: list[MealTrace],
    fat_g: float = 0.0,
    sugars_ratio: float = 0.3,
) -> dict[str, Any]:
    """Run full calibration suite against meal set.
    
    Args:
        forecast_func: Function that takes MealTotals and returns ForecastResult
        meals: List of MealTrace objects extracted from CGM data
        fat_g: Default fat grams for all meals
        sugars_ratio: Ratio of carbs that are sugars (default 0.3)
    
    Returns aggregate statistics and outliers.
    """
    results = []
    for meal in meals:
        # Create mock MealTotals and forecast
        from demo.forecast_engine import MealTotals
        
        totals = MealTotals(
            carbs_g=meal.carbs_g,
            sugars_g=meal.carbs_g * sugars_ratio,
            fat_g=fat_g if meal.fat_g is None else meal.fat_g,
        )
        forecast = forecast_func(totals)
        
        comparison = compare_forecast_to_trace(forecast, meal)
        comparison["meal_time"] = meal.meal_time
        results.append(comparison)
    
    # Aggregate stats
    peak_errors = [r["peak_error_mgdl"] for r in results if r["peak_error_mgdl"]]
    time_errors = [r["time_error_min"] for r in results if r["time_error_min"]]
    
    return {
        "total_meals": len(meals),
        "mean_peak_error": statistics.mean(peak_errors) if peak_errors else 0,
        "mean_time_error": statistics.mean(time_errors) if time_errors else 0,
        "max_peak_error": max(peak_errors) if peak_errors else 0,
        "max_time_error": max(time_errors) if time_errors else 0,
        "good_calibration_pct": sum(1 for r in results if r["calibration_status"] == "good") / len(results) * 100 if results else 0,
        "outliers": [r for r in results if r["calibration_status"] in ("warning", "poor")],
    }

# ── Drift Detection ──

def detect_drift(comparison: dict, threshold_pct: float = 0.15) -> dict:
    """Detect if forecast drift exceeds threshold.
    
    Args:
        comparison: Result from compare_forecast_to_trace()
        threshold_pct: Alert if error > 15% of actual peak
    
    Returns:
        dict with drift status and recommendations
    """
    actual_peak = comparison["actual_peak"] or 1
    peak_error = comparison["peak_error_mgdl"]
    
    drift_pct = peak_error / actual_peak if actual_peak else 0
    is_drifted = drift_pct > threshold_pct
    
    return {
        "is_drifted": is_drifted,
        "drift_pct": round(drift_pct, 2),
        "threshold_pct": threshold_pct,
        "recommendation": (
            "update_calibration" if is_drifted else "within_tolerance"
        ),
    }


def summarize_calibration_results(
    suite_results: dict,
    drift_threshold_pct: float = 0.15,
) -> dict:
    """Summarize calibration results with drift detection.
    
    Adds drift flags and recommendations.
    """
    # Flag outliers as potential drift
    drifted_meals = []
    for outlier in suite_results.get("outliers", []):
        drift = detect_drift(outlier, drift_threshold_pct)
        if drift["is_drifted"]:
            drifted_meals.append({
                "meal_time": outlier["meal_time"],
                "drift_pct": drift["drift_pct"],
            })
    
    return {
        **suite_results,
        "drifted_meals": drifted_meals,
        "avg_drift_pct": statistics.mean(
            [d["drift_pct"] for d in drifted_meals]
        ) if drifted_meals else 0,
        "needs_calibration_update": len(drifted_meals) >= 3,
    }
