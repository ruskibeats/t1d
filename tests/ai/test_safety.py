"""Unit tests for the SafetyScaffold module."""

import pytest
from app.ai.safety import SafetyScaffold


def test_safety_scaffold_import():
    """Test that SafetyScaffold can be imported."""
    from app.ai.safety import SafetyScaffold
    assert SafetyScaffold is not None


def test_safety_scaffold_instantiation():
    """Test that SafetyScaffold can be instantiated."""
    scaffold = SafetyScaffold()
    assert scaffold is not None
    assert hasattr(scaffold, 'build_guardrails')
    assert hasattr(scaffold, 'validate')
    assert hasattr(scaffold, 'contains_emergency_keywords')


def test_build_guardrails_diabetes_emergency():
    """Test build_guardrails for diabetes_emergency condition."""
    scaffold = SafetyScaffold()
    
    guardrails = scaffold.build_guardrails("diabetes_emergency")
    assert isinstance(guardrails, list)
    assert len(guardrails) > 0
    assert any("NEVER provide insulin dosing recommendations" in g for g in guardrails)
    assert any("ALWAYS recommend seeking immediate medical attention" in g for g in guardrails)
    
    guardrails_critical = scaffold.build_guardrails("diabetes_emergency", "critical")
    assert any("CRITICAL:" in g for g in guardrails_critical)
    
    guardrails_info = scaffold.build_guardrails("diabetes_emergency", "info")
    assert any("INFO:" in g for g in guardrails_info)


def test_build_guardrails_mental_health_crisis():
    """Test build_guardrails for mental_health_crisis condition."""
    scaffold = SafetyScaffold()
    guardrails = scaffold.build_guardrails("mental_health_crisis")
    assert isinstance(guardrails, list)
    assert len(guardrails) > 0
    assert any("ALWAYS provide crisis hotline information" in g for g in guardrails)
    assert any("NEVER minimize or dismiss the user's feelings" in g for g in guardrails)


def test_build_guardrails_general_medical():
    """Test build_guardrails for general_medical condition."""
    scaffold = SafetyScaffold()
    guardrails = scaffold.build_guardrails("general_medical")
    assert isinstance(guardrails, list)
    assert len(guardrails) > 0
    assert any("NEVER provide specific medical treatment instructions" in g for g in guardrails)
    assert any("ALWAYS recommend consulting a healthcare provider" in g for g in guardrails)


def test_build_guardrails_invalid_condition():
    """Test build_guardrails with invalid condition."""
    scaffold = SafetyScaffold()
    guardrails = scaffold.build_guardrails("invalid_condition")
    assert isinstance(guardrails, list)


def test_validate_severe_low_blood_sugar():
    """Test that 'severe low blood sugar' flags requires_escalation=True."""
    scaffold = SafetyScaffold()
    result = scaffold.validate("I'm having a severe low blood sugar episode", {"source": "user"})
    assert result["requires_escalation"] == True
    assert result["safety_level"] == "critical"
    assert result["is_safe"] == False
    assert "diabetes_emergency" in result["matched_conditions"]


def test_validate_normal_glucose_question():
    """Test that normal glucose questions are safe."""
    scaffold = SafetyScaffold()
    result = scaffold.validate("What was my blood sugar at 3pm?", {"source": "user"})
    assert result["is_safe"] == True
    assert result["safety_level"] == "safe"
    assert result["requires_escalation"] == False
    assert len(result["matched_conditions"]) == 0


def test_validate_mental_health_keywords():
    """Test mental health crisis keywords."""
    scaffold = SafetyScaffold()
    result = scaffold.validate("I want to hurt myself", {"source": "user"})
    assert result["requires_escalation"] == True
    assert result["safety_level"] == "critical"
    assert result["is_safe"] == False
    assert "mental_health_crisis" in result["matched_conditions"]


def test_validate_general_medical_emergency():
    """Test general medical emergency keywords."""
    scaffold = SafetyScaffold()
    result = scaffold.validate("I'm having chest pain and can't breathe", {"source": "user"})
    assert result["requires_escalation"] == True
    assert result["safety_level"] == "warning"
    assert result["is_safe"] == False
    assert "general_medical" in result["matched_conditions"]


def test_validate_assistant_source():
    """Test validation works with assistant source."""
    scaffold = SafetyScaffold()
    result = scaffold.validate("I want to kill myself", {"source": "assistant"})
    assert result["requires_escalation"] == True
    assert result["safety_level"] == "critical"
    
    result = scaffold.validate("Here's some educational information about diabetes", {"source": "assistant"})
    assert result["is_safe"] is True


def test_validate_empty_content():
    """Test validation with empty content."""
    scaffold = SafetyScaffold()
    result = scaffold.validate("", {"source": "user"})
    assert result["is_safe"] is True
    assert result["safety_level"] == "safe"
    assert result["requires_escalation"] == False


def test_validate_none_context():
    """Test validation with None context."""
    scaffold = SafetyScaffold()
    result = scaffold.validate("severe low blood sugar", None)
    assert result["requires_escalation"] is True
    assert result["safety_level"] == "critical"


def test_contains_emergency_keywords():
    """Test the backward-compatible contains_emergency_keywords method."""
    scaffold = SafetyScaffold()
    assert scaffold.contains_emergency_keywords("severe low") is True
    assert scaffold.contains_emergency_keywords("I want to die") is True
    assert scaffold.contains_emergency_keywords("What's my glucose?") is False
    assert scaffold.contains_emergency_keywords("") is False


def test_guardrails_are_condition_specific():
    """Test that different conditions return different guardrails."""
    scaffold = SafetyScaffold()
    
    diabetes_guardrails = scaffold.build_guardrails("diabetes_emergency")
    mental_health_guardrails = scaffold.build_guardrails("mental_health_crisis")
    general_guardrails = scaffold.build_guardrails("general_medical")
    
    diabetes_text = " ".join(diabetes_guardrails)
    mental_health_text = " ".join(mental_health_guardrails)
    general_text = " ".join(general_guardrails)
    
    assert "insulin dosing" in diabetes_text
    assert "insulin dosing" not in mental_health_text
    assert "crisis hotline" in mental_health_text
    assert "crisis hotline" not in diabetes_text
    assert "medical treatment instructions" in general_text


def test_policy_violation_dosing_advice():
    """Test that insulin dosing instructions are flagged."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate(
        "You should take 5 units of insulin now",
        {"source": "assistant"}
    )
    assert result["safety_level"] in ("critical", "warning")
    assert any("dosing" in r.lower() for r in result["reasons"])


def test_policy_violation_treatment_change():
    """Test that treatment plan changes are flagged."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate(
        "You should stop taking your insulin",
        {"source": "assistant"}
    )
    assert result["safety_level"] in ("critical", "warning")


def test_policy_violation_missing_disclaimer():
    """Test that long responses without disclaimer are flagged."""
    scaffold = SafetyScaffold()
    
    long_response = "Here is some medical information. " * 50
    result = scaffold.validate(long_response, {"source": "assistant"})
    assert any("disclaimer" in r.lower() for r in result["reasons"])


def test_no_false_positive_on_educational_content():
    """Test that educational content doesn't trigger false positives."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate(
        "Educational insights suggest that monitoring glucose after meals can identify patterns. "
        "Consider discussing with your diabetes care team for personalized strategies.",
        {"source": "assistant"}
    )
    assert result["is_safe"] is True


def test_no_false_positive_on_educational_content_long():
    """Test that long educational content with disclaimer doesn't trigger false positive."""
    scaffold = SafetyScaffold()
    
    long_educational = (
        "Educational insights suggest that monitoring glucose after meals can identify patterns. "
        "Based on similar patterns in your data, post-dinner spikes often occur when meals are higher in carbs. "
        "Some strategies to explore include eating earlier if possible, balancing carbs with protein and fiber. "
        "Remember: these are educational insights, not medical advice. "
        "Consider discussing these patterns with your diabetes care team for personalized strategies."
    )
    result = scaffold.validate(long_educational, {"source": "assistant"})
    assert result["is_safe"] is True


def test_assistant_source_with_emergency_keywords():
    """Test that emergency keywords in assistant output are flagged."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate(
        "If you want to kill yourself, call 911",
        {"source": "assistant"}
    )
    assert result["is_safe"] is False


def test_assistant_source_safe_response():
    """Test that normal assistant responses pass."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate(
        "Based on your recent patterns, your time in range is 78%. "
        "Consider discussing these trends with your healthcare team.",
        {"source": "assistant"}
    )
    assert result["is_safe"] is True


def test_severity_critical_for_diabetes_emergency():
    """Test that diabetes emergency keywords produce critical severity."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate("severe low blood sugar", {"source": "user"})
    assert result["safety_level"] == "critical"
    assert result["requires_escalation"] is True


def test_severity_warning_for_general_medical():
    """Test that general medical keywords produce warning severity."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate("I need help", {"source": "user"})
    assert result["safety_level"] == "warning"


def test_severity_safe_for_normal_query():
    """Test that normal queries are safe."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate("What was my glucose at noon?", {"source": "user"})
    assert result["safety_level"] == "safe"
    assert result["requires_escalation"] is False


def test_guardrails_all_severities():
    """Test that all severity levels produce different guardrails."""
    scaffold = SafetyScaffold()
    
    for condition in ["diabetes_emergency", "mental_health_crisis", "general_medical"]:
        for severity in ["info", "warning", "critical"]:
            guardrails = scaffold.build_guardrails(condition, severity)
            assert len(guardrails) > 0
            assert severity.upper() in guardrails[0] or severity in guardrails[0].lower()


def test_validate_whitespace_only():
    """Test validation with whitespace-only content."""
    scaffold = SafetyScaffold()
    result = scaffold.validate("   \n\t  ", {"source": "user"})
    assert result["is_safe"] is True


def test_validate_very_long_content():
    """Test validation with very long content."""
    scaffold = SafetyScaffold()
    long_text = "glucose reading was normal. " * 1000
    result = scaffold.validate(long_text, {"source": "user"})
    assert result["is_safe"] is True


def test_validate_mixed_case_keywords():
    """Test that keyword detection is case-insensitive."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate("SEVERE LOW BLOOD SUGAR", {"source": "user"})
    assert result["is_safe"] is False
    
    result = scaffold.validate("CaN't WaKe", {"source": "user"})
    assert result["is_safe"] is False


def test_validate_multiple_conditions():
    """Test content that matches multiple condition categories."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate(
        "severe low blood sugar and I want to hurt myself",
        {"source": "user"}
    )
    assert result["is_safe"] is False
    assert len(result["matched_conditions"]) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
