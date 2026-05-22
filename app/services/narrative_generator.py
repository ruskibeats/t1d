"""Deterministic narrative template generator for meal forecasts.

Generates safe, consistent user-facing explanations from structured forecast evidence.
"""

from typing import Optional

from app.services.meal_forecast_engine import MealForecast, RiskLevel
from app.services.safety_validator import validate_text_output


def generate_narrative(forecast: MealForecast) -> str:
    """Generate deterministic narrative from forecast.
    
    Args:
        forecast: MealForecast with risk level and evidence
        
    Returns:
        Narrative string grounded in evidence fields only
    """
    sections = []
    
    # Meal summary
    sections.append(_meal_summary_section(forecast))
    
    # Risk explanation
    sections.append(_risk_explanation_section(forecast))
    
    # Timing window
    sections.append(_timing_section(forecast))
    
    # Confidence note
    sections.append(_confidence_section(forecast))
    
    # Safety note
    sections.append("This is educational context from your data patterns, not medical advice.")
    
    narrative = " ".join(sections)
    
    # Safety validate even though we control the templates
    result = validate_text_output(narrative)
    return result.sanitized_text


def _meal_summary_section(forecast: MealForecast) -> str:
    """Generate meal summary section."""
    risk_descriptions = {
        RiskLevel.LOW: "This meal has a light carbohydrate load.",
        RiskLevel.MODERATE: "This meal has a moderate carbohydrate load.",
        RiskLevel.HIGH: "This meal has a higher carbohydrate load.",
        RiskLevel.VERY_HIGH: "This meal has a very high carbohydrate load.",
    }
    return risk_descriptions.get(forecast.risk_level, "This meal has notable carbohydrate content.")


def _risk_explanation_section(forecast: MealForecast) -> str:
    """Generate risk explanation section."""
    if forecast.delayed_effect:
        return "High fat content may delay the glucose response. "
    return ""


def _timing_section(forecast: MealForecast) -> str:
    """Generate timing window section."""
    onset = forecast.timing_onset_window
    peak = forecast.peak_window
    
    return f"Glucose changes typically begin {onset.earliest_minutes}-{onset.latest_minutes} minutes after eating, peaking around {peak.earliest_minutes}-{peak.latest_minutes} minutes. "


def _confidence_section(forecast: MealForecast) -> str:
    """Generate confidence section."""
    confidence = forecast.confidence
    if confidence >= 0.8:
        return "The forecast has high confidence based on your recent data. "
    elif confidence >= 0.6:
        return "The forecast has moderate confidence. Consider monitoring your response. "
    else:
        return "The forecast has limited confidence due to sparse data. Monitor closely. "


def rewrite_narrative_with_llm(narrative: str, feature_flag: bool = False) -> str:
    """Optionally rewrite narrative via LLM.
    
    Only called if feature flag is enabled, and safety validator runs after.
    
    Args:
        narrative: Base narrative to rewrite
        feature_flag: Whether LLM rewrite is enabled
        
    Returns:
        Original or rewritten narrative
    """
    if not feature_flag:
        return narrative
    
    # In production, this would call an LLM service
    # For now, return original
    return narrative