---
name: phase2-safety-llm-tests
description: Writes unit tests for the SafetyScaffold (expand existing) and LLMService in the T1D Companion. Covers policy violations, provider fallback chain, prompt building, and context assembly. Use when implementing Phase 2 safety and LLM tests.
model: z-ai/glm-4.5-air:free
context: fork
---

# Phase 2: Safety + LLM Service Unit Tests

## Task

Two test files:
1. **Expand `tests/ai/test_safety.py`** — add tests for policy violations, assistant-source validation, severity levels
2. **Create `tests/test_llm_service.py`** — unit tests for LLMService (mocking external HTTP calls)

## Part 1: Expand Safety Tests

Add these tests to the existing `tests/ai/test_safety.py`:

### Policy Violation Detection

```python
def test_policy_violation_dosing_advice():
    """Test that insulin dosing instructions are flagged."""
    scaffold = SafetyScaffold()
    
    # Should flag dosing advice
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
    
    long_response = "Here is some medical information. " * 50  # > 200 chars
    result = scaffold.validate(long_response, {"source": "assistant"})
    # Should get a warning about missing disclaimer
    assert any("disclaimer" in r.lower() for r in result["reasons"])

def test_no_false_positive_on_educational_content():
    """Test that educational content doesn't trigger false positives."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate(
        "Educational insights suggest that monitoring glucose after meals can help identify patterns. "
        "Consider discussing with your care team.",
        {"source": "assistant"}
    )
    assert result["is_safe"] is True
```

### Assistant-Source Validation

```python
def test_assistant_source_with_emergency_keywords():
    """Test that emergency keywords in assistant output are flagged."""
    scaffold = SafetyScaffold()
    
    result = scaffold.validate(
        "If you want to kill yourself, call 911",
        {"source": "assistant"}
    )
    # Should flag the emergency keywords
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
```

### Severity Levels

```python
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
```

### Guardrail Building

```python
def test_guardrails_all_severities():
    """Test that all severity levels produce different guardrails."""
    scaffold = SafetyScaffold()
    
    for condition in ["diabetes_emergency", "mental_health_crisis", "general_medical"]:
        for severity in ["info", "warning", "critical"]:
            guardrails = scaffold.build_guardrails(condition, severity)
            assert len(guardrails) > 0
            # First guardrail should contain the severity label
            assert severity.upper() in guardrails[0] or severity in guardrails[0].lower()

def test_guardrails_invalid_condition():
    """Test guardrails with unknown condition."""
    scaffold = SafetyScaffold()
    guardrails = scaffold.build_guardrails("nonexistent_condition")
    assert isinstance(guardrails, list)
```

### Edge Cases

```python
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
```

## Part 2: LLM Service Tests

Create `tests/test_llm_service.py`:

### Mock HTTP Transport

```python
import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

class MockTransport(httpx.AsyncBaseTransport):
    """Mock HTTP transport for testing LLM API calls."""
    
    def __init__(self, responses):
        self.responses = responses
        self.request_count = 0
    
    async def handle_async_request(self, request):
        if self.request_count < len(self.responses):
            resp = self.responses[self.request_count]
            self.request_count += 1
            if isinstance(resp, Exception):
                raise resp
            return httpx.Response(
                status_code=resp.get("status", 200),
                json=resp.get("body", {}),
            )
        return httpx.Response(status_code=200, json={"choices": [{"message": {"content": "test"}}]})
```

### Fixtures

```python
@pytest.fixture
def llm_service():
    from app.services.llm_service import LLMService
    return LLMService(provider="openrouter", api_key="test-key", model="test-model")

@pytest.fixture
def mock_openrouter_response():
    return {
        "status": 200,
        "body": {
            "choices": [{"message": {"content": "Your glucose trends look stable."}}],
            "usage": {"total_tokens": 150},
        },
    }

@pytest.fixture
def mock_openai_response():
    return {
        "status": 200,
        "body": {
            "choices": [{"message": {"content": "Based on your data..."}}],
            "usage": {"total_tokens": 200},
        },
    }

@pytest.fixture
def mock_anthropic_response():
    return {
        "status": 200,
        "body": {
            "content": [{"text": "Your patterns suggest..."}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        },
    }
```

### Tests

```python
@pytest.mark.asyncio
async def test_retrieve_context_structure(llm_service, db_session, test_user):
    """Test that retrieve_context returns the correct structure."""
    ctx = await llm_service.retrieve_context(db_session, test_user.id)
    
    assert hasattr(ctx, 'recent_glucose')
    assert hasattr(ctx, 'recent_events')
    assert hasattr(ctx, 'pattern_summary')
    assert hasattr(ctx, 'user_profile')
    assert isinstance(ctx.recent_glucose, list)
    assert isinstance(ctx.recent_events, list)

@pytest.mark.asyncio
async def test_retrieve_context_user_profile(llm_service, db_session, test_user):
    """Test that user profile is correctly populated."""
    ctx = await llm_service.retrieve_context(db_session, test_user.id)
    
    assert ctx.user_profile is not None
    assert ctx.user_profile["diabetes_type"] == "Type 1"
    assert ctx.user_profile["target_range_low"] == 70
    assert ctx.user_profile["target_range_high"] == 180

@pytest.mark.asyncio
async def test_retrieve_context_empty_data(llm_service, db_session, test_user):
    """Test retrieve_context with no glucose or events."""
    ctx = await llm_service.retrieve_context(db_session, test_user.id)
    
    assert ctx.recent_glucose == []
    assert ctx.recent_events == []

@pytest.mark.asyncio
async def test_retrieve_context_with_glucose(llm_service, db_session, test_user, glucose_readings):
    """Test that glucose readings are retrieved."""
    ctx = await llm_service.retrieve_context(db_session, test_user.id)
    
    assert len(ctx.recent_glucose) > 0
    assert ctx.recent_glucose[0]["value"] is not None

@pytest.mark.asyncio
async def test_retrieve_context_with_events(llm_service, db_session, test_user, context_events):
    """Test that events are retrieved."""
    ctx = await llm_service.retrieve_context(db_session, test_user.id)
    
    assert len(ctx.recent_events) > 0
    assert ctx.recent_events[0]["type"] is not None

@pytest.mark.asyncio
async def test_build_system_prompt_includes_profile(llm_service):
    """Test that system prompt includes user profile."""
    from app.services.llm_service import RAGContext
    
    ctx = RAGContext(
        user_profile={
            "diabetes_type": "Type 1",
            "target_range_low": 70,
            "target_range_high": 180,
        }
    )
    prompt = llm_service._build_system_prompt(ctx)
    
    assert "Type 1" in prompt
    assert "70-180" in prompt

@pytest.mark.asyncio
async def test_build_system_prompt_includes_patterns(llm_service):
    """Test that system prompt includes pattern summary."""
    from app.services.llm_service import RAGContext
    
    ctx = RAGContext(
        pattern_summary={
            "time_in_range_percentage": 78.5,
            "estimated_a1c": 7.2,
            "post_meal_spike_count": 3,
        }
    )
    prompt = llm_service._build_system_prompt(ctx)
    
    assert "78.5" in prompt
    assert "7.2" in prompt

@pytest.mark.asyncio
async def test_build_system_prompt_includes_events(llm_service):
    """Test that system prompt includes recent events."""
    from app.services.llm_service import RAGContext
    
    ctx = RAGContext(
        recent_events=[
            {"type": "meal", "carbs_grams": 65, "timestamp": "2024-01-15T19:30:00"},
        ]
    )
    prompt = llm_service._build_system_prompt(ctx)
    
    assert "meal" in prompt

@pytest.mark.asyncio
async def test_build_conversation_history(llm_service):
    """Test conversation history formatting."""
    from app.services.llm_service import ConversationTurn
    
    turns = [
        ConversationTurn(role="user", content="Hello"),
        ConversationTurn(role="assistant", content="Hi there!"),
        ConversationTurn(role="user", content="What's my glucose?"),
    ]
    history = llm_service._build_conversation_history(turns)
    
    assert len(history) == 3
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"

@pytest.mark.asyncio
async def test_build_conversation_history_max_turns(llm_service):
    """Test that max_turns limits history."""
    from app.services.llm_service import ConversationTurn
    
    turns = [ConversationTurn(role="user", content=f"msg{i}") for i in range(20)]
    history = llm_service._build_conversation_history(turns, max_turns=5)
    
    assert len(history) == 5

@pytest.mark.asyncio
async def test_call_openrouter_success(llm_service, mock_openrouter_response):
    """Test successful OpenRouter API call."""
    transport = MockTransport([mock_openrouter_response])
    
    with patch.object(llm_service, '_get_openrouter_key', return_value='test-key'):
        with patch('httpx.AsyncClient.__new__', return_value=httpx.AsyncClient(transport=transport)):
            messages = [{"role": "user", "content": "test"}]
            # This test verifies the method structure; actual HTTP is mocked
            # The real test would need more sophisticated mocking

@pytest.mark.asyncio
async def test_provider_enum_values():
    """Test LLMProvider enum has expected values."""
    from app.services.llm_service import LLMProvider
    
    assert LLMProvider.OPENAI == "openai"
    assert LLMProvider.ANTHROPIC == "anthropic"
    assert LLMProvider.OPENROUTER == "openrouter"

@pytest.mark.asyncio
async def test_default_model_per_provider():
    """Test that each provider has a correct default model."""
    from app.services.llm_service import LLMService, LLMProvider
    
    openai_service = LLMService(provider=LLMProvider.OPENAI, api_key="test")
    assert "gpt" in openai_service.model.lower()
    
    anthropic_service = LLMService(provider=LLMProvider.ANTHROPIC, api_key="test")
    assert "claude" in anthropic_service.model.lower()
    
    openrouter_service = LLMService(provider=LLMProvider.OPENROUTER, api_key="test")
    assert "gpt-4o" in openrouter_service.model
```

## Critical Rules

1. **Only modify `tests/ai/test_safety.py` and create `tests/test_llm_service.py`**
2. **Don't modify any source code** — these are pure tests
3. **Mock all external HTTP calls** — never hit real APIs
4. **Use the fixtures from conftest.py** for DB-dependent tests
5. **Minimum 25 tests total** across both files
6. **All tests must pass with `pytest tests/ai/test_safety.py tests/test_llm_service.py -x -v`**

## Verification

After writing, verify:
- [ ] `tests/ai/test_safety.py` has at least 20 test functions (existing + new)
- [ ] `tests/test_llm_service.py` has at least 15 test functions
- [ ] Policy violation tests cover: dosing advice, treatment changes, missing disclaimer
- [ ] Assistant-source tests cover: emergency keywords in output, safe responses
- [ ] LLM service tests cover: context retrieval, prompt building, history formatting, provider defaults
- [ ] All tests use `@pytest.mark.asyncio` where needed
- [ ] `pytest tests/ai/test_safety.py tests/test_llm_service.py -x -v` passes

## Output

Write your implementation notes to: `PHASE2_W6_SAFETY_LLM_TESTS.md`
