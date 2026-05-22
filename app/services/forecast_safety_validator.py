"""Safety validator for meal forecast outputs.

Enforces hard safety boundaries to prevent forecast outputs from including
insulin dose suggestions, correction advice, or medical dosing guidance.
"""

import re
from typing import List, Tuple

from app.services.meal_forecast_engine import MealForecast


# Forbidden patterns that indicate dosing advice or medical guidance
FORBIDDEN_PHRASES = [
    # Direct dosing suggestions
    r'\d+\s*(?:unit|iu|ml)\s*(?:of)?\s*insulin',
    r'(?:take|inject|administer)\s+(?:a\s+)?(?:bolus|correction)',
    r'bolus\s+(?:for|to\s+cover)',
    
    # Correction factor suggestions
    r'correction\s+(?:bolus|dose|factor)',
    r'cf\s*=',
    r'correction\s+factor',
    
    # Ratio-based dosing
    r'\d+\s*:\s*\d+\s*ratio',
    r'carb\s+ratio',
    r'insulin-to-carb',
    
    # Dosage calculations
    r'(?:divide|split)\s+(?:by|into)',
    r'calculate.*\binsulin\b',
    r'dose.*\binsulin\b',
    
    # Medical instruction phrasing
    r'you\s+should\s+(?:take|inject|administer)',
    r'you\s+need\s+to\s+(?:take|inject)',
    r'recommend.*\binsulin',
    
    # Strong directive language for dosing
    r'apply.*\bdose\b',
    r'program.*\bpump\b',
    r'set.*\brate\b.*\binsulin',
]

FORBIDDEN_KEYWORDS = [
    'bolus', 'correction', 'dose', 'dosing', 'inject', 'insulin-to-carb',
    'correction factor', 'carb ratio', 'insulin sensitivity',
]


class ForecastValidationError(Exception):
    """Raised when forecast output fails safety validation."""
    pass


def validate_forecast_text(text: str) -> Tuple[bool, List[str]]:
    """Validate forecast text for safety violations.
    
    Args:
        text: The text to validate
        
    Returns:
        Tuple of (is_valid, list of violations found)
    """
    violations = []
    
    # Check forbidden phrases using regex
    for pattern in FORBIDDEN_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(f"Forbidden pattern matched: {pattern}")
    
    # Check forbidden keywords in dangerous contexts
    lower_text = text.lower()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in lower_text:
            violations.append(f"Forbidden keyword detected: {keyword}")
    
    return len(violations) == 0, violations


def sanitize_forecast_narrative(narrative: str) -> str:
    """Sanitize forecast narrative by removing/approximating dangerous content.
    
    Args:
        narrative: The narrative text to sanitize
        
    Returns:
        Sanitized narrative safe for output
    """
    sanitized = narrative
    
    # Remove dosing suggestions
    for pattern in FORBIDDEN_PHRASES:
        sanitized = re.sub(pattern, '[REMOVED - dosing guidance]', sanitized, flags=re.IGNORECASE)
    
    # Replace forbidden keywords with safe alternatives
    replacements = {
        'bolus': 'meal insulin',
        'correction': 'adjustment',
        'dose': 'amount',
        'dosing': 'calculations',
    }
    
    for keyword, replacement in replacements.items():
        # Only replace if not in safe context
        pattern = rf'\b{keyword}\b'
        if re.search(pattern, sanitized, re.IGNORECASE):
            # Check if it's in a dosing context
            for dose_pattern in [r'\d+\s*unit', r'\d+\s*iu', r'for.*insulin']:
                if re.search(dose_pattern, sanitized, re.IGNORECASE):
                    sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


def validate_forecast_output(forecast: MealForecast, narrative: str = "") -> Tuple[bool, List[str]]:
    """Validate complete forecast output for safety.
    
    Checks both structured forecast and any narrative text.
    
    Args:
        forecast: The MealForecast object to validate
        narrative: Optional narrative text
        
    Returns:
        Tuple of (is_valid, list of violations)
    """
    violations = []
    
    # Validate narrative if provided
    if narrative:
        valid, narrative_violations = validate_forecast_text(narrative)
        violations.extend(narrative_violations)
    
    # Check evidence for dangerous content
    for evidence in forecast.evidence:
        if evidence.value:
            valid, evidence_violations = validate_forecast_text(evidence.value)
            if not valid:
                violations.extend(evidence_violations)
    
    # Check that confidence is appropriately bounded
    if forecast.confidence > 0.95 and not forecast.is_reliable():
        violations.append("High confidence claimed without reliable evidence")
    
    return len(violations) == 0, violations


def ensure_safe_response(narrative: str, forecast: MealForecast) -> str:
    """Ensure response is safe, sanitizing if necessary.
    
    Args:
        narrative: The narrative to make safe
        forecast: The forecast for context
        
    Returns:
        Safe narrative for output
    """
    is_safe, violations = validate_forecast_output(forecast, narrative)
    
    if not is_safe:
        # Return a safe default narrative
        if forecast.is_reliable():
            return (
                f"This meal has a {forecast.risk_level} risk of glucose impact. "
                "Consider consulting your diabetes care team for personalized guidance."
            )
        else:
            return (
                "Unable to provide reliable forecast due to limited data. "
                "Please consult your diabetes care team for guidance."
            )
    
    return sanitize_forecast_narrative(narrative)


# Disclaimer that should appear with all forecasts
FORECAST_DISCLAIMER = (
    "This forecast is for educational purposes only and does not constitute "
    "medical advice. Individual responses may vary. Always consult your "
    "healthcare provider before making changes to your diabetes management."
)