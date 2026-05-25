"""Unit tests for the LLMService module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.llm_service import LLMService, LLMProvider, RAGContext, ConversationTurn


@pytest.fixture
def llm_service():
    return LLMService(provider="openrouter", api_key="test-key", model="test-model")


@pytest.fixture
def llm_service_openai():
    return LLMService(provider="openai", api_key="test-key", model="gpt-4o-mini")


@pytest.fixture
def llm_service_anthropic():
    return LLMService(provider="anthropic", api_key="test-key", model="claude-3-5-haiku")


class TestLLMProvider:
    def test_provider_enum_values(self):
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.OPENROUTER == "openrouter"

    def test_default_model_openai(self):
        service = LLMService(provider=LLMProvider.OPENAI, api_key="test")
        assert "gpt" in service.model.lower()

    def test_default_model_anthropic(self):
        # Need to pass model=None to test default model behavior
        service = LLMService(provider=LLMProvider.ANTHROPIC, api_key="test", model=None)
        # The config has llm_model set, so we check if it's using config or provider default
        assert service.model is not None

    def test_default_model_openrouter(self):
        service = LLMService(provider=LLMProvider.OPENROUTER, api_key="test")
        assert "gpt-4o" in service.model


class TestRAGContext:
    def test_empty_context(self):
        ctx = RAGContext()
        assert ctx.recent_glucose == []
        assert ctx.recent_events == []
        assert ctx.pattern_summary is None
        assert ctx.user_profile is None

    def test_context_with_data(self):
        ctx = RAGContext(
            recent_glucose=[{"value": 120, "trend": "flat"}],
            recent_events=[{"type": "meal", "carbs_grams": 45}],
            pattern_summary={"time_in_range_percentage": 78.5},
            user_profile={"diabetes_type": "Type 1"},
        )
        assert len(ctx.recent_glucose) == 1
        assert ctx.recent_glucose[0]["value"] == 120
        assert ctx.pattern_summary["time_in_range_percentage"] == 78.5


class TestConversationTurn:
    def test_conversation_turn_creation(self):
        turn = ConversationTurn(role="user", content="Hello")
        assert turn.role == "user"
        assert turn.content == "Hello"

    def test_conversation_turn_with_timestamp(self):
        from datetime import datetime
        ts = datetime(2024, 1, 1, 12, 0, 0)
        turn = ConversationTurn(role="assistant", content="Hi", timestamp=ts)
        assert turn.timestamp == ts


class TestBuildSystemPrompt:
    def test_build_prompt_includes_profile(self, llm_service):
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

    def test_build_prompt_includes_patterns(self, llm_service):
        ctx = RAGContext(
            pattern_summary={
                "time_in_range": {"percentage": 78.5},
                "estimated_a1c": 7.2,
                "post_meal_spike_count": 3,
            }
        )
        prompt = llm_service._build_system_prompt(ctx)
        assert "78.5" in prompt
        assert "7.2" in prompt

    def test_build_prompt_includes_events(self, llm_service):
        ctx = RAGContext(
            recent_events=[
                {"type": "meal", "carbs_grams": 65, "timestamp": "2024-01-15T19:30:00"},
            ]
        )
        prompt = llm_service._build_system_prompt(ctx)
        assert "meal" in prompt

    def test_build_prompt_includes_graph_edges(self, llm_service):
        ctx = RAGContext(
            graph_edges=[
                {
                    "edge_type": "meal_to_glucose_spike",
                    "source_metric_id": 1,
                    "target_metric_id": 2,
                    "confidence": 0.82,
                    "time_delay_seconds": 7200,
                    "evidence": {"food_name": "Pizza", "glucose_rise": 90},
                }
            ]
        )
        prompt = llm_service._build_system_prompt(ctx)
        assert "Recent Personal Relationship Evidence" in prompt
        assert "meal_to_glucose_spike" in prompt
        assert "confidence 0.82" in prompt
        assert "observational evidence only" in prompt

    def test_build_prompt_no_data(self, llm_service):
        ctx = RAGContext()
        prompt = llm_service._build_system_prompt(ctx)
        assert "T1D Companion" in prompt
        assert "EDUCATIONAL" in prompt


class TestBuildConversationHistory:
    def test_build_history_basic(self, llm_service):
        turns = [
            ConversationTurn(role="user", content="Hello"),
            ConversationTurn(role="assistant", content="Hi there!"),
        ]
        history = llm_service._build_conversation_history(turns)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"

    def test_build_history_max_turns(self, llm_service):
        turns = [ConversationTurn(role="user", content=f"msg{i}") for i in range(20)]
        history = llm_service._build_conversation_history(turns, max_turns=5)
        assert len(history) == 5

    def test_build_history_empty(self, llm_service):
        history = llm_service._build_conversation_history([])
        assert history == []


class TestProviderKeyRetrieval:
    def test_get_openrouter_key_none_when_not_configured(self, llm_service):
        # Without env vars set, should return None
        import os
        original = os.environ.get('OPENROUTER_API_KEY')
        try:
            if 'OPENROUTER_API_KEY' in os.environ:
                del os.environ['OPENROUTER_API_KEY']
            key = llm_service._get_openrouter_key()
            assert key is None
        finally:
            if original:
                os.environ['OPENROUTER_API_KEY'] = original

    def test_get_openai_key_none_when_not_configured(self, llm_service):
        import os
        original = os.environ.get('OPENAI_API_KEY')
        try:
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
            key = llm_service._get_openai_key()
            assert key is None
        finally:
            if original:
                os.environ['OPENAI_API_KEY'] = original

    def test_get_anthropic_key_none_when_not_configured(self, llm_service):
        import os
        original = os.environ.get('ANTHROPIC_API_KEY')
        try:
            if 'ANTHROPIC_API_KEY' in os.environ:
                del os.environ['ANTHROPIC_API_KEY']
            key = llm_service._get_anthropic_key()
            assert key is None
        finally:
            if original:
                os.environ['ANTHROPIC_API_KEY'] = original


class TestRuleBasedResponse:
    @pytest.mark.asyncio
    async def test_fallback_glucose_query(self, llm_service):
        ctx = RAGContext(
            recent_glucose=[
                {"value": 140, "trend": "flat", "timestamp": "2024-01-15T12:00:00"},
                {"value": 135, "trend": "rising", "timestamp": "2024-01-15T11:30:00"},
            ],
        )
        result = await llm_service._rule_based_response("What's my glucose?", ctx)
        assert "140" in result["response"]
        assert result["provider"] == "fallback"
        assert result["tokens_used"] == 0

    @pytest.mark.asyncio
    async def test_fallback_pattern_query(self, llm_service):
        ctx = RAGContext(
            pattern_summary={
                "time_in_range_percentage": 78.5,
                "estimated_a1c": 7.2,
                "post_meal_spike_count": 3,
                "overnight_low_count": 1,
            }
        )
        result = await llm_service._rule_based_response("What are my patterns?", ctx)
        assert "78.5" in result["response"]

    @pytest.mark.asyncio
    async def test_fallback_meal_query(self, llm_service):
        ctx = RAGContext(
            recent_events=[
                {"type": "meal", "carbs_grams": 65, "timestamp": "2024-01-15T19:30:00"},
            ],
        )
        result = await llm_service._rule_based_response("What did I eat?", ctx)
        assert "meal" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_fallback_insulin_query_no_dosing(self, llm_service):
        ctx = RAGContext()
        result = await llm_service._rule_based_response("How much insulin should I take?", ctx)
        assert "can't provide dosing" in result["response"].lower() or "healthcare team" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_fallback_help_query(self, llm_service):
        ctx = RAGContext()
        result = await llm_service._rule_based_response("What can you help me with?", ctx)
        assert "glucose" in result["response"].lower() or "patterns" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_fallback_empty_data(self, llm_service):
        ctx = RAGContext()
        result = await llm_service._rule_based_response("Hello", ctx)
        assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_fallback_no_dosing_advice(self, llm_service):
        ctx = RAGContext()
        result = await llm_service._rule_based_response("Tell me how much insulin to take", ctx)
        response_lower = result["response"].lower()
        # Should NOT contain specific dosing numbers
        assert "units" not in response_lower or "care team" in response_lower


# =========================================================================
# Provider Pool Tests
# =========================================================================

class TestProviderPoolParsing:
    """Tests for LLMService.parse_provider_pool()."""

    def test_empty_string_returns_empty_list(self):
        assert LLMService.parse_provider_pool("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert LLMService.parse_provider_pool("   ") == []

    def test_single_entry(self):
        result = LLMService.parse_provider_pool("openrouter/deepseek/deepseek-v4-flash:free")
        assert result == [("openrouter", "deepseek/deepseek-v4-flash:free")]

    def test_multiple_entries(self):
        result = LLMService.parse_provider_pool(
            "openrouter/deepseek/deepseek-v4-flash:free,openrouter/owl-alpha"
        )
        assert result == [
            ("openrouter", "deepseek/deepseek-v4-flash:free"),
            ("openrouter", "owl-alpha"),
        ]

    def test_model_only_uses_default_provider(self):
        result = LLMService.parse_provider_pool("gpt-4o-mini", default_provider="openai")
        assert result == [("openai", "gpt-4o-mini")]

    def test_mixed_entries(self):
        result = LLMService.parse_provider_pool(
            "openrouter/deepseek/deepseek-v4-flash:free,gpt-4o-mini",
            default_provider="openai",
        )
        assert result == [
            ("openrouter", "deepseek/deepseek-v4-flash:free"),
            ("openai", "gpt-4o-mini"),
        ]

    def test_strips_whitespace(self):
        result = LLMService.parse_provider_pool("  openrouter/deepseek/deepseek-v4-flash:free , openrouter/owl-alpha  ")
        assert result == [
            ("openrouter", "deepseek/deepseek-v4-flash:free"),
            ("openrouter", "owl-alpha"),
        ]


class TestProviderPoolIntegration:
    """Integration tests for provider pool in LLMService."""

    def test_service_loads_pool_from_config(self):
        svc = LLMService(provider="openrouter", api_key="test-key", model="test-model")
        # Default pool has free model fallbacks
        assert len(svc.provider_pool) >= 1
        assert svc.provider_pool[0][0] == "openrouter"

    def test_service_accepts_explicit_pool(self):
        pool = [("openrouter", "deepseek/deepseek-v4-flash:free")]
        svc = LLMService(
            provider="openrouter", api_key="test-key", model="test-model",
            provider_pool=pool,
        )
        assert svc.provider_pool == pool

    @pytest.mark.asyncio
    async def test_rotation_fallback_on_primary_failure(self):
        """When primary provider fails, try pool entries."""
        from app.services.llm_service import LLMServiceError

        pool = [("openrouter", "deepseek/deepseek-v4-flash:free")]
        svc = LLMService(
            provider="openai", api_key="bad-key", model="gpt-4o-mini",
            provider_pool=pool,
        )

        call_count = 0

        async def mock_call_llm(messages, max_tokens, stream):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LLMServiceError("OpenAI failed")
            return {
                "response": "fallback response",
                "tokens_used": 10,
                "model": "deepseek-v4-flash",
                "provider": "openrouter",
                "streamed": False,
                "safety_flagged": False,
            }

        with patch.object(svc, "_call_llm", side_effect=mock_call_llm), \
             patch.object(svc, "retrieve_context", new_callable=AsyncMock) as mock_ctx, \
             patch.object(svc, "_get_conversation_history", new_callable=AsyncMock):
            mock_ctx.return_value = RAGContext()
            result = await svc.generate_response(
                "test message", AsyncMock(), user_id=1
            )

        assert call_count == 2
        assert result["response"] == "fallback response"

    @pytest.mark.asyncio
    async def test_all_providers_fail_returns_rule_based(self):
        """When all providers fail, fall back to rule-based response."""
        from app.services.llm_service import LLMServiceError

        pool = [("openrouter", "deepseek/deepseek-v4-flash:free")]
        svc = LLMService(
            provider="openai", api_key="bad-key", model="gpt-4o-mini",
            provider_pool=pool,
        )

        async def mock_call_llm_fail(messages, max_tokens, stream):
            raise LLMServiceError("All providers failed")

        with patch.object(svc, "_call_llm", side_effect=mock_call_llm_fail), \
             patch.object(svc, "retrieve_context", new_callable=AsyncMock) as mock_ctx, \
             patch.object(svc, "_get_conversation_history", new_callable=AsyncMock):
            mock_ctx.return_value = RAGContext()
            result = await svc.generate_response(
                "test message", AsyncMock(), user_id=1
            )

        assert result["model"] == "rule-based-fallback"
        assert result["provider"] == "fallback"

    @pytest.mark.asyncio
    async def test_primary_success_no_rotation(self):
        """When primary provider succeeds, no rotation needed."""
        svc = LLMService(
            provider="openrouter", api_key="test-key", model="test-model",
            provider_pool=[("openrouter", "other-model")],
        )

        async def mock_call_llm(messages, max_tokens, stream):
            return {
                "response": "primary response",
                "tokens_used": 10,
                "model": svc.model,
                "provider": svc.provider.value,
                "streamed": False,
                "safety_flagged": False,
            }

        with patch.object(svc, "_call_llm", side_effect=mock_call_llm), \
             patch.object(svc, "retrieve_context", new_callable=AsyncMock) as mock_ctx, \
             patch.object(svc, "_get_conversation_history", new_callable=AsyncMock):
            mock_ctx.return_value = RAGContext()
            result = await svc.generate_response(
                "test message", AsyncMock(), user_id=1
            )

        assert result["response"] == "primary response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
