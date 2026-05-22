---
name: "forecast-output-safety-validator"
description: "Build a safety validator for meal forecast outputs that blocks dosing advice, validates structured forecast objects, sanitizes narratives while preserving educational content, and ensures confidence is bounded by reliability. Use for any health AI feature that produces educational forecasts (glucose impact, meal timing, risk prediction) without crossing into medical advice territory."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Forecast Output Safety Validator

## When to Use

Build a safety validator for structured forecast outputs in health AI applications. Use when:

- Creating meal impact forecasts, glucose rise timing predictions, or risk scores
- Output must be educational insight WITHOUT crossing into dosing/treatment guidance
- Need to validate both structured data objects AND free-text narratives
- Require evidence validation and confidence-bound checking
- Building any feature that predicts physiological responses to user actions

Do NOT use for:

- General chat safety (use `global:post-llm-safety-validation`)
- Non-health forecasts or predictions
- Features that intentionally provide medical dosing advice (those need formal regulatory clearance)

## Procedure

### 1. Define forbidden patterns for your domain

Start with broad medical dosing patterns, then specialize for your specific domain:

```python
# Base patterns (shared across health AI)
FORBIDDEN_PHRASES = [
    r'\d+\s*(?:unit|iu|ml)\s*(?:of)?\s*insulin',
    r'(?:take|inject|administer)\s+(?:a\s+)?(?:bolus|correction)',
    r'bolus\s+(?:for|to\s+cover)',
    r'correction\s+(?:bolus|dose|factor)',
    r'carb\s+ratio',
    r'insulin-to-carb',
]

# Domain-specific patterns
FORECAST_DOMAIN_PHRASES = [
    r'you\s+should\s+(?:take|inject|administer)',
    r'you\s+need\s+to\s+(?:take|inject)',
    r'recommend.*\binsulin',
    r'apply.*\bdose\b',
]
```

### 2. Define forbidden keywords with context awareness

Some keywords are only dangerous in specific contexts:

```python
FORBIDDEN_KEYWORDS = [
    'bolus', 'correction', 'dose', 'dosing', 'inject',
    'insulin-to-carb', 'correction factor', 'carb ratio',
]

# Note: "meal insulin" is SAFE - context matters
```

### 3. Create the text validation function

```python
import re
from typing import List, Tuple

def validate_forecast_text(text: str) -> Tuple[bool, List[str]]:
    """Validate forecast text for safety violations."""
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
```

### 4. Create narrative sanitization

Sanitize while preserving educational content:

```python
def sanitize_forecast_narrative(narrative: str) -> str:
    """Sanitize forecast narrative by removing/approximating dangerous content."""
    sanitized = narrative
    
    # Remove dosing suggestions
    for pattern in FORBIDDEN_PHRASES:
        sanitized = re.sub(
            pattern, 
            '[REMOVED - dosing guidance]', 
            sanitized, 
            flags=re.IGNORECASE
        )
    
    # Replace forbidden keywords with safe alternatives
    replacements = {
        'bolus': 'meal insulin',
        'correction': 'adjustment',
        'dose': 'amount',
        'dosing': 'calculations',
    }
    
    for keyword, replacement in replacements.items():
        pattern = rf'\b{keyword}\b'
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized
```

### 5. Create structured forecast validation

Validate the forecast object itself, not just text:

```python
def validate_forecast_output(forecast, narrative: str = "") -> Tuple[bool, List[str]]:
    """Validate complete forecast output for safety."""
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
    
    # Check confidence bounds
    if forecast.confidence > 0.95 and not forecast.is_reliable():
        violations.append("High confidence claimed without reliable evidence")
    
    return len(violations) == 0, violations
```

### 6. Create safe response generator

Ensure any output is safe, handling both clean and dangerous inputs:

```python
def ensure_safe_response(narrative: str, forecast) -> str:
    """Ensure response is safe, sanitizing if necessary."""
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
```

### 7. Write comprehensive tests

```python
class TestValidateForecastText:
    def test_clean_text_passes(self):
        text = "This meal has moderate carbohydrate content."
        is_valid, violations = validate_forecast_text(text)
        assert is_valid is True
        assert violations == []

    def test_bolus_detection(self):
        text = "You should take a bolus of 4 units for this meal."
        is_valid, violations = validate_forecast_text(text)
        assert is_valid is False
        assert len(violations) > 0

    def test_safe_meal_insulin_phrase(self):
        text = "This requires meal insulin consideration."
        is_valid, violations = validate_forecast_text(text)
        assert is_valid is True  # "meal insulin" is safe

class TestSanitizeForecastNarrative:
    def test_sanitize_removes_dosing(self):
        narrative = "You should take a correction bolus of 2 units."
        sanitized = sanitize_forecast_narrative(narrative)
        assert "correction" not in sanitized.lower()
        assert "bolus" not in sanitized.lower()
        assert "[REMOVED" in sanitized

    def test_sanitize_preserves_educational_content(self):
        narrative = "This meal has 45g carbs which is moderate."
        sanitized = sanitize_forecast_narrative(narrative)
        assert "moderate" in sanitized
```

## Pitfalls

- **Context matters**: "meal insulin" is safe; "bolus" is dangerous. Don't blanket-ban keywords without considering context
- **Evidence validation is critical**: Dangerous content can hide in structured evidence fields, not just narrative text
- **Confidence bounds**: High confidence claims require reliable evidence - check `is_reliable()` before trusting confidence scores
- **Sanitization preserves meaning**: When removing dosing language, keep the educational insight. Replace "take a bolus" concepts with "meal insulin consideration"
- **Safe defaults for dangerous input**: Always have a fallback safe narrative that doesn't expose what was blocked
- **Test edge cases**: "0.5 units" should be caught; "notes on your levels" should not be flagged as dosing

## Verification

1. **Clean educational text passes**: "This meal has moderate carbs" → valid, no violations
2. **Dosing advice blocked**: "Take 3 units of insulin" → blocked, violation detected
3. **Treatment changes blocked**: "Stop taking your insulin" → blocked
4. **Evidence fields validated**: Dangerous content in `forecast.evidence` triggers violations
5. **Confidence bounds enforced**: High confidence (>0.95) without `is_reliable()` returns violation
6. **Sanitization works**: Dangerous text → "[REMOVED - dosing guidance]" with safe replacement
7. **All tests pass**: Full test suite with all scenarios covered
8. **Safe fallback**: `ensure_safe_response()` returns appropriate disclaimer for dangerous input