#!/usr/bin/env python3
"""Versioned T1D LLM context block for companion prompts.

This is the single source of truth for diabetes context injection.
Version 1.0 - Initial release.
"""

from __future__ import annotations

T1D_LLM_CONTEXT_v1 = {
    "version": "1.0",
    "description": "Companion-only diabetes context, not for dosing decisions",
    
    # State variables for LLM awareness
    "state_variables": [
        "current_glucose",   # Most recent CGM (mg/dL)
        "trend",             # Rate of change (-2 to +2 arrows)
        "iob",               # Insulin on board (units)
        "cob",               # Carbs on board (grams)
        "activity",          # Insulin activity (0-1)
    ],
    
    # BANNED - controller language
    "banned_words": [
        "insulin", "bolus", "injection", "dose", "deliver",
        "pump", "basal", "temp basal", "TBR",
        "SMB", "microbolus", "correction",
    ],
    
    # APPROVED - companion patterns
    "approved_patterns": [
        "glucose may rise",
        "peak around {value} mg/dL at {time}",
        "range {low}-{high} mg/dL",
        "similar meals showed...",
        "monitor closely",
    ],
    
    # Profile traits
    "anchor_types": {
        "well_controlled": {
            "rise_per_g": 1.5,
            "balance_factor": 1.2,
            "description": "Standard meal response, reliable patterns",
        },
        "high_fat_delayed": {
            "rise_per_g": 3.0,
            "balance_factor": 1.35,
            "description": "High fat/protein extends absorption 3-6 hours",
        },
        "post_meal_spike": {
            "rise_per_g": 3.0,
            "balance_factor": 2.0,
            "description": "Spikes high quickly, use caution",
        },
        "exercise_sensitive": {
            "rise_per_g": 1.5,
            "balance_factor": 1.1,
            "description": "Exercise lowers post-meal rise",
        },
    },
    
    # Safety triggers
    "safety_triggers": {
        "large_meal": "carbs_g >= 80",
        "high_fat": "fat_g >= 15",
        "high_peak": "predicted_peak > 250",
        "low_drop": "predicted_min < 70",
    },
    
    # Evidence requirements
    "required_evidence_fields": [
        "top_drivers",
        "historical_similarity_score",
        "profile_assumptions",
        "missing_information_flags",
    ],
}


def get_context(version: str = "1.0") -> dict:
    """Get the LLM context block for a specific version."""
    if version == "1.0":
        return T1D_LLM_CONTEXT_v1
    raise ValueError(f"Unknown version: {version}")


def check_safety(forecast_result, totals_dict: dict = None) -> list[str]:
    """Check safety constraints against forecast result.
    
    Args:
        forecast_result: ForecastResult from forecast_engine
        totals_dict: Optional carbs/fat dict (from CompanionState.totals)
    
    Returns list of warning messages for large/high-risk meals.
    """
    warnings = []
    
    # Get totals from either argument or forecast meal_drivers
    carbs = (totals_dict or {}).get("carbs_g", 0)
    fat = (totals_dict or {}).get("fat_g", 0)
    
    if carbs >= 80:
        warnings.append("large meal, consider splitting over time")
    if fat >= 15:
        warnings.append("fat may extend or delay the rise")
    if forecast_result.peak_mg_dl > 250:
        warnings.append("monitor closely, glucose may go high")
    
    return warnings