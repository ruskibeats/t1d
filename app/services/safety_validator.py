"""Safety validator for meal forecast outputs.

Enforces hard safety boundaries to prevent dosing advice leakage.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from app.services.meal_forecast_engine import MealForecast


# Forbidden phrases that indicate dosing advice
FORBIDDEN_PHRASES = [
    # Insulin units
    r"\b\d+(\.\d+)?\s*(units?|u)\s*(of\s*)?(insulin|bolus|correction)",
    r"\btake\s+\d+\s*(units?|u)",
    r"\bdose\s+\d+\s*(units?|u)",
    
    # Correction advice
    r"correction\s+(bolus|dose)",
    r"give\s+(yourself\s+)?\d+\s*(units?|u)",
    
    # Bolus timing
    r"bolus\s+(now|immediately|before|after)",
    r"inject\s+\d+",
    
    # Dose equivalence
    r"\d+\s*(grams|carbs?)\s*=\s*\d+\s*(units?|u)",
    r"ratio\s*:\s*\d+[:/]\d+",
    
    # Direct dosing
    r"you\s+(should|must|need to)\s+(take|give|inject)",
    r"(take|give|inject)\s+\d+\s*(units?|u)",
]

# Compile patterns for efficiency
FORBIDDEN_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PHRASES]

# Prohibited field keys
PROHIBITED_FIELDS = [
    "insulin_units",
    "bolus_amount",
    "correction_dose",
    "dose_recommendation",
    "units_to_take",
    "recommended_dose",
]


@dataclass
class SafetyResult:
    """Result of safety validation."""
    is_safe: bool
    violations: List[str]
    sanitized_text: Optional[str] = None


def validate_forecast_output(forecast: MealForecast) -> SafetyResult:
    """Validate that forecast output doesn't contain dosing advice.
    
    Checks the forecast object for prohibited fields and patterns.
    
    Args:
        forecast: MealForecast to validate
        
    Returns:
        SafetyResult with validation outcome
    """
    violations = []
    
    # Check for prohibited fields in the forecast
    forecast_dict = forecast.__dict__
    for field in PROHIBITED_FIELDS:
        if field in forecast_dict:
            violations.append(f"Prohibited field found: {field}")
    
    # Check evidence for forbidden phrases
    for evidence in forecast.evidence:
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(evidence.value):
                violations.append(f"Forbidden phrase in evidence '{evidence.key}': {evidence.value}")
    
    return SafetyResult(
        is_safe=len(violations) == 0,
        violations=violations,
    )


def validate_text_output(text: str) -> SafetyResult:
    """Validate text output for safety violations.
    
    Scans text for forbidden phrases indicating dosing advice.
    
    Args:
        text: Text to validate
        
    Returns:
        SafetyResult with validation outcome and sanitized text if needed
    """
    violations = []
    sanitized = text
    
    for pattern in FORBIDDEN_PATTERNS:
        match = pattern.search(text)
        if match:
            matched_text = match.group(0)
            violations.append(f"Forbidden phrase detected: {matched_text}")
            sanitized = sanitized.replace(matched_text, "[REDACTED]")
    
    return SafetyResult(
        is_safe=len(violations) == 0,
        violations=violations,
        sanitized_text=sanitized if violations else text,
    )


def enforce_safety(forecast: MealForecast, text: Optional[str] = None) -> tuple[MealForecast, Optional[str], List[str]]:
    """Enforce safety on forecast and optional text.
    
    Either strips unsafe content or returns violations.
    
    Args:
        forecast: MealForecast to check
        text: Optional text narrative to validate
        
    Returns:
        Tuple of (safe_forecast, safe_text, violations)
    """
    # Validate forecast
    forecast_result = validate_forecast_output(forecast)
    
    # Remove prohibited fields if present
    safe_forecast = forecast
    if not forecast_result.is_safe:
        # Create clean forecast without prohibited fields
        safe_fields = {k: v for k, v in forecast.__dict__.items() 
                       if k not in PROHIBITED_FIELDS}
        safe_forecast = MealForecast(**safe_fields)
    
    # Validate text if provided
    safe_text = text
    text_violations = []
    if text:
        text_result = validate_text_output(text)
        safe_text = text_result.sanitized_text
        text_violations = text_result.violations
    
    all_violations = forecast_result.violations + text_violations
    
    return safe_forecast, safe_text, all_violations


def log_safety_event(violations: List[str], source: str = "forecast"):
    """Log a safety intervention event.
    
    Args:
        violations: List of violation descriptions
        source: Source of the violation (for logging)
    """
    # In production, this would log to an audit system
    # For now, we just ensure the violations are tracked
    pass