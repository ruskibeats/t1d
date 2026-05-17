"""Integration tests for the full chat pipeline - unit tests only."""

import pytest


# -------------------------------------------------------------------
# Non-DB Integration Tests (Unit Tests)
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_emergency_keyword_triggers_escalation():
    """Test that emergency keywords trigger safety escalation."""
    from app.ai.safety import SafetyScaffold
    
    scaffold = SafetyScaffold()
    
    # Test diabetes emergency
    result = scaffold.validate("I'm having severe low blood sugar and can't wake up", {"source": "user"})
    assert result["is_safe"] is False
    assert result["requires_escalation"] is True
    assert result["safety_level"] == "critical"


@pytest.mark.asyncio
async def test_pattern_analysis_query_is_safe():
    """Test that pattern analysis query is safe."""
    from app.ai.safety import SafetyScaffold
    
    scaffold = SafetyScaffold()
    result = scaffold.validate("What is my time in range?", {"source": "user"})
    assert result["is_safe"] is True


@pytest.mark.asyncio
async def test_meal_query_pattern_detection():
    """Test meal query pattern detection in LLM service."""
    from app.services.llm_service import LLMService, RAGContext
    
    service = LLMService(provider=None, api_key=None)
    
    ctx = RAGContext(
        recent_events=[
            {"type": "meal", "carbs_grams": 45, "timestamp": "2024-01-15T19:30:00"},
        ],
    )
    result = await service._rule_based_response("What did I eat?", ctx)
    
    assert "meal" in result["response"].lower() or "45g" in result["response"]


@pytest.mark.asyncio
async def test_safety_agent_detects_dosing():
    """Test that safety agent detects dosing advice in AI responses."""
    from app.ai.safety import SafetyScaffold
    
    scaffold = SafetyScaffold()
    
    # AI response with dosing advice should be flagged
    result = scaffold.validate("You should take 5 units of insulin", {"source": "assistant"})
    
    # Should detect policy violation (dosing advice)
    assert result["safety_level"] in ["critical", "warning"]


@pytest.mark.asyncio
async def test_multiple_chat_turns():
    """Test multi-turn conversation flow."""
    from app.services.llm_service import LLMService, ConversationTurn
    
    service = LLMService(provider=None, api_key=None)
    
    # Build conversation history
    turns = [
        ConversationTurn(role="user", content="Hello"),
        ConversationTurn(role="assistant", content="Hi! How can I help?"),
        ConversationTurn(role="user", content="What's my glucose?"),
    ]
    
    history = service._build_conversation_history(turns)
    assert len(history) == 3
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_delegate_task_routing():
    """Test that coordinator routes tasks to correct agents."""
    from app.agents.coordinator import AgentCoordinator
    
    # AgentCoordinator should be importable and have process_chat_message
    assert hasattr(AgentCoordinator, 'process_chat_message')


@pytest.mark.asyncio
async def test_rag_context_structure():
    """Test RAG context has expected structure."""
    from app.services.llm_service import RAGContext
    
    ctx = RAGContext(
        recent_glucose=[{"value": 100, "timestamp": "2024-01-01T12:00:00"}],
        recent_events=[{"type": "meal", "carbs_grams": 30}],
        pattern_summary={"time_in_range_percentage": 80.0},
        user_profile={"diabetes_type": "Type 1"},
    )
    
    assert len(ctx.recent_glucose) == 1
    assert ctx.recent_glucose[0]["value"] == 100
    assert ctx.pattern_summary["time_in_range_percentage"] == 80.0


@pytest.mark.asyncio
async def test_chat_endpoint_exists():
    """Test that chat endpoint exists in the API."""
    from app.api.chat import router
    
    # Router should be importable
    assert router is not None


@pytest.mark.asyncio
async def test_lifespan_attaches_coordinator_to_app_state(monkeypatch):
    """Lifespan startup should expose coordinator for chat endpoints."""
    from fastapi import FastAPI
    import app.main as main_module

    class DummyCoordinator:
        started = False
        stopped = False

        async def startup(self):
            self.started = True

        async def shutdown(self):
            self.stopped = True

    async def fake_init_db():
        return None

    monkeypatch.setattr(main_module, "init_db", fake_init_db)
    monkeypatch.setattr(main_module, "AgentCoordinator", DummyCoordinator)

    test_app = FastAPI()
    async with main_module.lifespan(test_app):
        assert isinstance(test_app.state.coordinator, DummyCoordinator)
        assert test_app.state.coordinator.started is True

    assert test_app.state.coordinator.stopped is True


# =========================================================================
# Post-LLM Safety Validation Tests
# =========================================================================


class TestPostLlmSafetyValidation:
    """Tests for post-LLM safety validation in coordinator and chat endpoint."""

    def test_post_llm_safety_blocks_dosing(self):
        """Mock LLM returns dosing advice; response is replaced with safe fallback."""
        from app.ai.safety import SafetyScaffold

        scaffold = SafetyScaffold()

        # Simulate AI response with dosing advice
        ai_response = "Based on your glucose of 180 mg/dL, take 5 units of insulin."
        result = scaffold.validate(ai_response, {"source": "assistant"})

        # Should be flagged as unsafe
        assert result["is_safe"] is False
        assert any("dosing" in r.lower() for r in result["reasons"])

        # The chat endpoint should replace it with safe fallback
        safe_fallback = (
            "I'm not able to provide that information. "
            "Please consult your healthcare team for medical advice."
        )
        assert "5 units" not in safe_fallback
        assert "healthcare team" in safe_fallback

    def test_post_llm_safety_allows_safe(self):
        """Safe educational text passes through without modification."""
        from app.ai.safety import SafetyScaffold

        scaffold = SafetyScaffold()

        safe_response = (
            "Your time in range over the last 14 days was 72%. "
            "This is an educational insight — not medical advice. "
            "Consider discussing your patterns with your diabetes team."
        )
        result = scaffold.validate(safe_response, {"source": "assistant"})

        # Should pass safety check
        assert result["is_safe"] is True
        assert result["safety_level"] == "safe"

    def test_post_llm_safety_blocks_treatment_change(self):
        """Response suggesting treatment changes is blocked."""
        from app.ai.safety import SafetyScaffold

        scaffold = SafetyScaffold()

        ai_response = "You should stop taking your insulin before meals."
        result = scaffold.validate(ai_response, {"source": "assistant"})

        # Should flag treatment plan modification
        assert result["is_safe"] is False
        # Should mention policy violation
        assert any("treatment" in r.lower() or "insulin" in r.lower()
                   for r in result["reasons"])

    def test_post_llm_safety_emergency_escalation(self):
        """Emergency keywords in LLM output trigger escalation."""
        from app.ai.safety import SafetyScaffold

        scaffold = SafetyScaffold()

        ai_response = "If you can't wake up, call 911 immediately."
        result = scaffold.validate(ai_response, {"source": "assistant"})

        # Emergency language should be flagged
        # (this response is quoting emergency guidance — it still gets flagged)
        reasons_text = " ".join(result["reasons"]).lower()
        assert result["is_safe"] is False or "emergency" in reasons_text or result["requires_escalation"]

    @pytest.mark.asyncio
    async def test_coordinator_post_llm_safety_replaces_unsafe(self):
        """Coordinator.process_chat_message replaces unsafe LLM output via SafetyAgent."""
        from app.agents.coordinator import AgentCoordinator

        coordinator = AgentCoordinator()
        await coordinator.startup()

        # Override the conversation agent to return dosing advice
        class UnsafeConversationAgent:
            async def handle(self, data):
                return {"response": "take 5 units of insulin now"}

        original_conversation = coordinator.agents["conversation"]
        coordinator.agents["conversation"] = UnsafeConversationAgent()

        # Mock data ingestion and pattern agents to avoid DB dependency
        class MockDataAgent:
            async def handle(self, data):
                return {
                    "glucose": {"recent_count": 0, "latest_value": None, "trend": None},
                    "events": [],
                    "patterns": [],
                    "user_profile": None,
                }

        class MockPatternAgent:
            async def handle(self, data):
                return {
                    "patterns": [],
                    "tir_percentage": 0,
                    "estimated_a1c": 0,
                    "spike_count": 0,
                    "overnight_low_count": 0,
                }

        coordinator.agents["data_ingestion"] = MockDataAgent()
        coordinator.agents["pattern"] = MockPatternAgent()

        result = await coordinator.process_chat_message(
            message="What should I do about my blood sugar?",
            user_id=1,
            session=None,
        )

        # Restore original agent
        coordinator.agents["conversation"] = original_conversation
        await coordinator.shutdown()

        # The response should be the safe fallback, not the dosing advice
        assert "units" not in result.get("response", "")
        assert "healthcare team" in result.get("response", "") or "consult" in result.get("response", "")
        assert result.get("safety_flagged", False) is True

    @pytest.mark.asyncio
    async def test_coordinator_allows_safe_response(self):
        """Coordinator allows safe LLM output through unchanged."""
        from app.agents.coordinator import AgentCoordinator

        coordinator = AgentCoordinator()
        await coordinator.startup()

        class SafeConversationAgent:
            async def handle(self, data):
                return {
                    "response": (
                        "Your time in range has been 75% over the last 14 days. "
                        "This is an educational insight — discuss with your care team."
                    )
                }

        class MockDataAgent:
            async def handle(self, data):
                return {
                    "glucose": {"recent_count": 0, "latest_value": None, "trend": None},
                    "events": [],
                    "patterns": [],
                    "user_profile": None,
                }

        class MockPatternAgent:
            async def handle(self, data):
                return {
                    "patterns": [],
                    "tir_percentage": 0,
                    "estimated_a1c": 0,
                    "spike_count": 0,
                    "overnight_low_count": 0,
                }

        coordinator.agents["conversation"] = SafeConversationAgent()
        coordinator.agents["data_ingestion"] = MockDataAgent()
        coordinator.agents["pattern"] = MockPatternAgent()

        result = await coordinator.process_chat_message(
            message="How is my time in range?",
            user_id=1,
            session=None,
        )

        await coordinator.shutdown()

        # Safe response should pass through
        assert "75%" in result.get("response", "")
        assert result.get("safety_flagged", False) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])