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
    
    # Test with warning severity (default)
    guardrails = scaffold.build_guardrails("diabetes_emergency")
    assert isinstance(guardrails, list)
    assert len(guardrails) > 0
    assert any("NEVER provide insulin dosing recommendations" in g for g in guardrails)
    assert any("ALWAYS recommend seeking immediate medical attention" in g for g in guardrails)
    
    # Test with critical severity
    guardrails_critical = scaffold.build_guardrails("diabetes_emergency", "critical")
    assert any("CRITICAL:" in g for g in guardrails_critical)
    
    # Test with info severity
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
    # Should return empty list or default guardrails
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
    assert result["safety_level"] == "warning"  # general_medical is warning level
    assert result["is_safe"] == False
    assert "general_medical" in result["matched_conditions"]


def test_validate_assistant_source():
    """Test validation works with assistant source."""
    scaffold = SafetyScaffold()
    # Test with emergency content from assistant
    result = scaffold.validate("I want to kill myself", {"source": "assistant"})
    assert result["requires_escalation"] == True
    assert result["safety_level"] == "critical"
    
    # Test with safe content from assistant
    result = scaffold.validate("Here's some educational information about diabetes", {"source": "assistant"})
    assert result["is_safe"] == True  # Should be safe if no emergency keywords


def test_validate_empty_content():
    """Test validation with empty content."""
    scaffold = SafetyScaffold()
    result = scaffold.validate("", {"source": "user"})
    assert result["is_safe"] == True
    assert result["safety_level"] == "safe"
    assert result["requires_escalation"] == False


def test_validate_none_context():
    """Test validation with None context."""
    scaffold = SafetyScaffold()
    result = scaffold.validate("severe low blood sugar", None)
    assert result["requires_escalation"] == True
    assert result["safety_level"] == "critical"


def test_contains_emergency_keywords():
    """Test the backward-compatible contains_emergency_keywords method."""
    scaffold = SafetyScaffold()
    assert scaffold.contains_emergency_keywords("severe low") == True
    assert scaffold.contains_emergency_keywords("I want to die") == True
    assert scaffold.contains_emergency_keywords("What's my glucose?") == False
    assert scaffold.contains_emergency_keywords("") == False


def test_guardrails_are_condition_specific():
    """Test that different conditions return different guardrails."""
    scaffold = SafetyScaffold()
    
    diabetes_guardrails = scaffold.build_guardrails("diabetes_emergency")
    mental_health_guardrails = scaffold.build_guardrails("mental_health_crisis")
    general_guardrails = scaffold.build_guardrails("general_medical")
    
    # They should have different content
    diabetes_text = " ".join(diabetes_guardrails)
    mental_health_text = " ".join(mental_health_guardrails)
    general_text = " ".join(general_guardrails)
    
    assert "insulin dosing" in diabetes_text
    assert "insulin dosing" not in mental_health_text
    assert "crisis hotline" in mental_health_text
    assert "crisis hotline" not in diabetes_text
    assert "medical treatment instructions" in general_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])