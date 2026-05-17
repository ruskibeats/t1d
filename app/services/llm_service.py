"""LLM Integration Service for T1D Conversational AI.

Integrates with OpenAI GPT-4o-mini and Anthropic Claude 3.5 Haiku
to provide natural language responses based on user's glucose data,
patterns, and context. Includes RAG (Retrieval-Augmented Generation)
for personalized responses.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.db.models import ContextEvent, Conversation, ConversationMessage, GlucoseReading, User
from app.core.errors import SafetyViolationError
from app.services.pattern_service import PatternService


logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers."""
    
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    MINIMAX = "minimax"


class ConversationTurn(BaseModel):
    """A single turn in a conversation."""
    
    role: str = Field(..., description="Role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")


class RAGContext(BaseModel):
    """Retrieved context for RAG."""
    
    recent_glucose: List[Dict[str, Any]] = Field(default_factory=list)
    recent_events: List[Dict[str, Any]] = Field(default_factory=list)
    pattern_summary: Optional[Dict[str, Any]] = Field(None)
    user_profile: Optional[Dict[str, Any]] = Field(None)


class LLMServiceError(Exception):
    """Raised when LLM service operations fail."""
    pass


class LLMService:
    """Service for LLM-powered conversational AI.
    
    Integrates with OpenAI and Anthropic models to provide:
    - Natural language responses to user queries
    - Pattern summarization in plain language
    - Context-aware conversation
    - Safety guardrails and content filtering
    
    Uses RAG (Retrieval-Augmented Generation) to ground responses
    in the user's actual glucose data and patterns.
    """
    
    @staticmethod
    def parse_provider_pool(pool_str: str, default_provider: str = "openrouter") -> list[tuple[str, str]]:
        """Parse comma-separated provider/model string into list of tuples.
        
        Args:
            pool_str: Comma-separated, e.g. "openrouter/deepseek/deepseek-v4-flash:free,openrouter/owl-alpha"
            default_provider: Provider to use when only model is specified
            
        Returns:
            List of (provider, model) tuples
        """
        if not pool_str or not pool_str.strip():
            return []
        entries = []
        for item in pool_str.split(","):
            item = item.strip()
            if not item:
                continue
            if "/" in item:
                provider, model = item.split("/", 1)
                entries.append((provider, model))
            else:
                entries.append((default_provider, item))
        return entries

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider_pool: Optional[list[tuple[str, str]]] = None,
    ):
        """Initialize LLM service.
        
        Args:
            provider: LLM provider (if None, uses config)
            api_key: API key (if None, uses env var)
            model: Model name (if None, uses default for provider)
            provider_pool: List of (provider, model) fallback pool
        """
        from app.config import get_settings
        config = get_settings()
        
        if provider is None:
            provider = LLMProvider(config.llm_provider)
        
        self.provider = provider
        self.api_key = api_key or config.openrouter_api_key
        self.model = model or config.llm_model or self._get_default_model()
        self.provider_pool = provider_pool if provider_pool is not None else config.parse_provider_pool()
        self.pattern_service = PatternService()
        self.logger = logging.getLogger(f"{__name__}.LLMService")
    
    def _get_default_model(self) -> str:
        """Get default model for provider."""
        if self.provider == LLMProvider.OPENAI:
            return "gpt-4o-mini"
        elif self.provider == LLMProvider.OPENROUTER:
            return "openai/gpt-4o-mini"
        elif self.provider == LLMProvider.MINIMAX:
            return "minimax/minimax-m2.5"
        return "claude-3-5-haiku-20241022"
    
    # -------------------------------------------------------------------
    # RAG (Retrieval-Augmented Generation)
    # -------------------------------------------------------------------
    
    async def retrieve_context(
        self,
        session: AsyncSession,
        user_id: int,
        time_range_days: int = 14,
    ) -> RAGContext:
        """Retrieve relevant context for RAG.
        
        Gathers recent glucose data, events, and pattern summaries
        to provide context for LLM responses.
        
        Args:
            session: Database session
            user_id: ID of the user
            time_range_days: Days of history to retrieve
            
        Returns:
            RAG context with relevant data
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=time_range_days)
        
        # Recent glucose readings (last 20)
        glucose_result = await session.execute(
            select(GlucoseReading)
            .where(
                GlucoseReading.user_id == user_id,
                GlucoseReading.timestamp >= start_date,
            )
            .order_by(GlucoseReading.timestamp.desc())
            .limit(20)
        )
        glucose_readings = glucose_result.scalars().all()
        
        recent_glucose = [
            {
                "timestamp": r.timestamp.isoformat(),
                "value": r.glucose_value,
                "trend": r.trend,
                "type": r.reading_type,
            }
            for r in glucose_readings
        ]
        
        # Recent events (last 10)
        events_result = await session.execute(
            select(ContextEvent)
            .where(
                ContextEvent.user_id == user_id,
                ContextEvent.timestamp >= start_date,
            )
            .order_by(ContextEvent.timestamp.desc())
            .limit(10)
        )
        events = events_result.scalars().all()
        
        recent_events = [
            {
                "timestamp": e.timestamp.isoformat(),
                "type": e.event_type,
                "subtype": e.event_subtype,
                "description": e.description,
                "carbs_grams": e.carbs_grams,
                "insulin_units": e.insulin_units,
            }
            for e in events
        ]
        
        # Pattern summary
        try:
            pattern_summary = await self.pattern_service.calculate_time_in_range(
                session, user_id, start_date, end_date
            )
        except Exception as e:
            self.logger.warning(f"Could not generate pattern summary: {e}")
            pattern_summary = None
        
        # User profile
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        user_profile = None
        if user:
            user_profile = {
                "diabetes_type": user.diabetes_type,
                "target_range_low": user.target_range_low,
                "target_range_high": user.target_range_high,
                "timezone": user.timezone,
                "glucose_units": user.glucose_units,
            }
        
        return RAGContext(
            recent_glucose=recent_glucose,
            recent_events=recent_events,
            pattern_summary=pattern_summary,
            user_profile=user_profile,
        )
    
    # -------------------------------------------------------------------
    # Prompt Generation
    # -------------------------------------------------------------------
    
    def _build_system_prompt(self, rag_context: RAGContext) -> str:
        """Build system prompt with RAG context.
        
        Args:
            rag_context: Retrieved context for RAG
            
        Returns:
            System prompt string
        """
        prompt = """You are T1D Companion, a helpful and supportive AI assistant for people with Type 1 Diabetes. Your role is to provide educational information, pattern recognition insights, and emotional support — but NEVER medical advice or dosing recommendations.

KEY PRINCIPLES:
- You are EDUCATIONAL, not clinical — never give dosing advice
- Acknowledge individual variability in diabetes management
- Be empathetic and non-judgmental
- Encourage discussion with healthcare providers
- Use clear, plain language (avoid medical jargon)
- Include "educational insight" phrasing for pattern observations

CONTEXT:
"""
        
        # Add user profile context
        if rag_context.user_profile:
            profile = rag_context.user_profile
            prompt += f"""
User Profile:
- Diabetes type: {profile.get('diabetes_type', 'Type 1')}
- Target range: {profile.get('target_range_low', 70)}-{profile.get('target_range_high', 180)} mg/dL
- Glucose units: {profile.get('glucose_units', 'mg/dL')}
"""
        
        # Add pattern summary
        if rag_context.pattern_summary:
            tir = rag_context.pattern_summary.get("time_in_range", {})
            prompt += f"""
Recent Pattern Summary (last 14 days):
- Time in range: {tir.get('percentage', 0):.1f}% (target 70-180 mg/dL)
- Time below range: {tir.get('below_range', {}).get('percentage', 0):.1f}%
- Time above range: {tir.get('above_range', {}).get('percentage', 0):.1f}%
- Estimated A1C: {rag_context.pattern_summary.get('estimated_a1c', 0)}
"""
        
        # Add recent events context
        if rag_context.recent_events:
            prompt += f"""
Recent Events ({len(rag_context.recent_events)} events in last {len(rag_context.recent_events)}):
"""
            for event in rag_context.recent_events[:5]:  # Show last 5
                prompt += f"- {event['timestamp'][:10]}: {event['type']}"
                if event.get('carbs_grams'):
                    prompt += f" ({event['carbs_grams']}g carbs)"
                prompt += "\n"
        
        # Add condition-specific safety guardrails
        from app.ai.safety import SafetyScaffold
        safety_scaffold = SafetyScaffold()
        guardrails = safety_scaffold.build_guardrails(condition="general_medical", severity="warning")
        guardrails_text = "\n".join([f"- {g}" for g in guardrails])
        
        prompt += f"""
SAFETY RULES:
{guardrails_text}
"""
        prompt += """
- Use phrases like "educational insights suggest", "patterns indicate", "consider discussing with your care team"

RESPONSE STYLE:
- Concise but thorough (2-4 sentences when possible)
- Acknowledge complexity and individual variation
- Offer supportive encouragement
- End with suggestion to discuss with healthcare team if relevant

Ready to help!"""
        
        return prompt
    
    def _build_conversation_history(self, turns: List[ConversationTurn], max_turns: int = 10) -> List[Dict[str, str]]:
        """Build conversation history for LLM.
        
        Args:
            turns: List of conversation turns
            max_turns: Maximum number of turns to include
            
        Returns:
            Formatted conversation history
        """
        history = []
        recent_turns = turns[-max_turns:]
        
        for turn in recent_turns:
            history.append({
                "role": turn.role,
                "content": turn.content,
            })
        
        return history
    
    # -------------------------------------------------------------------
    # Rule-Based Fallback Response
    # -------------------------------------------------------------------
    
    async def _rule_based_response(
        self,
        message: str,
        rag_context: RAGContext,
    ) -> Dict[str, Any]:
        """Generate a rule-based response when no LLM provider is available.
        
        Uses the RAG context to provide informative, grounded responses
        without calling any external API.
        """
        message_lower = message.lower()
        profile = rag_context.user_profile or {}
        glucose = rag_context.recent_glucose
        events = rag_context.recent_events
        patterns = rag_context.pattern_summary
        
        parts = []
        
        # Glucose query
        if any(word in message_lower for word in ["glucose", "blood sugar", "reading", "bg", "number"]):
            if glucose:
                latest = glucose[0]
                parts.append(f"Your most recent glucose reading was {latest['value']} mg/dL")
                if latest.get('trend'):
                    parts.append(f"trending {latest['trend']}")
                parts.append(f"at {latest['timestamp'][:16]}.")
                
                if len(glucose) > 1:
                    values = [g['value'] for g in glucose[:10]]
                    avg = sum(values) / len(values)
                    parts.append(f"Your average over the last {len(values)} readings is {avg:.0f} mg/dL.")
            else:
                parts.append("I don't have any recent glucose readings for you yet.")
        
        # Pattern/TIR query
        elif any(word in message_lower for word in ["pattern", "trend", "time in range", "tir", "a1c", "average"]):
            if patterns:
                tir = patterns.get("time_in_range_percentage", 0)
                a1c = patterns.get("estimated_a1c", 0)
                avg_glucose = patterns.get("average_glucose", 0)
                parts.append(f"Over the last 14 days:")
                parts.append(f"- Time in range (70-180 mg/dL): {tir:.1f}%")
                parts.append(f"- Estimated A1C: {a1c}")
                parts.append(f"- Average glucose: {avg_glucose:.0f} mg/dL")
                
                spikes = patterns.get("post_meal_spike_count", 0)
                if spikes:
                    parts.append(f"- Post-meal spikes detected: {spikes}")
                
                overnight = patterns.get("overnight_low_count", 0)
                if overnight:
                    parts.append(f"- Overnight low events: {overnight}")
            else:
                parts.append("I don't have enough data to analyze patterns yet. Keep logging your readings!")
        
        # Meal/food query
        elif any(word in message_lower for word in ["meal", "food", "eat", "carb", "spike after"]):
            meals = [e for e in events if e.get("type") == "meal"]
            if meals:
                parts.append(f"You've logged {len(meals)} meals in the last 14 days.")
                recent_meal = meals[0]
                if recent_meal.get("carbs_grams"):
                    parts.append(f"Your most recent meal had {recent_meal['carbs_grams']}g carbs at {recent_meal['timestamp'][:16]}.")
                
                if patterns and patterns.get("post_meal_spike_count", 0) > 0:
                    parts.append(f"I've detected {patterns['post_meal_spike_count']} post-meal spikes. Consider discussing meal timing and carb counting with your care team.")
            else:
                parts.append("I don't see any recent meal logs. Try logging your meals to see how they affect your glucose.")
        
        # Insulin query
        elif any(word in message_lower for word in ["insulin", "dose", "bolus", "basal", "unit"]):
            parts.append("I can see your insulin data, but I can't provide dosing recommendations.")
            parts.append("Always follow your healthcare team's guidance for insulin dosing.")
            insulin_events = [e for e in events if e.get("type") == "insulin"]
            if insulin_events:
                parts.append(f"You have {len(insulin_events)} insulin entries logged.")
        
        # Exercise query
        elif any(word in message_lower for word in ["exercise", "activity", "workout", "walk", "run"]):
            exercises = [e for e in events if e.get("type") == "exercise"]
            if exercises:
                parts.append(f"You've logged {len(exercises)} exercise sessions recently.")
                parts.append("Exercise can lower glucose during and after activity. Monitor closely and carry fast-acting glucose.")
            else:
                parts.append("I don't see any recent exercise logs. Regular activity can help with glucose management.")
        
        # Help/general query
        elif any(word in message_lower for word in ["help", "what can", "how do", "hello", "hi"]):
            parts.append("I'm your T1D Companion! I can help you understand patterns in your diabetes data.")
            parts.append("Try asking me about:")
            parts.append("- Your recent glucose readings and trends")
            parts.append("- Time in range and estimated A1C")
            parts.append("- Post-meal spikes and patterns")
            parts.append("- How meals, exercise, and insulin relate to your glucose")
            parts.append("Remember: I provide educational insights, not medical advice. Always consult your healthcare team for treatment decisions.")
        
        # Fallback for unrecognized queries
        else:
            parts.append("I can help you understand patterns in your diabetes data.")
            if glucose:
                parts.append(f"Your latest glucose was {glucose[0]['value']} mg/dL.")
            if patterns:
                parts.append(f"Your time in range is {patterns.get('time_in_range_percentage', 0):.1f}%.")
            parts.append("Try asking about your glucose trends, patterns, meals, or exercise.")
        
        response = " ".join(parts)
        
        return {
            "response": response,
            "tokens_used": 0,
            "model": "rule-based-fallback",
            "provider": "fallback",
            "streamed": False,
            "safety_flagged": False,
        }
    
    # -------------------------------------------------------------------
    # LLM Query Methods
    # -------------------------------------------------------------------
    
    async def generate_response(
        self,
        message: str,
        session: AsyncSession,
        user_id: int,
        conversation_id: Optional[int] = None,
        stream: bool = False,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Generate AI response to user message.
        
        Args:
            message: User message
            session: Database session
            user_id: ID of the user
            conversation_id: Optional conversation ID
            stream: Whether to stream response
            max_tokens: Maximum tokens in response
            
        Returns:
            Response with text and metadata
        """
        # Safety check first
        from app.ai.safety import SafetyScaffold
        safety_scaffold = SafetyScaffold()
        safety_result = safety_scaffold.validate(message, {"source": "user"})
        if not safety_result["is_safe"]:
            return {
                "response": (
                    "I'm concerned about what you're describing. "
                    "If you're experiencing severe symptoms, please seek immediate medical attention or call emergency services. "
                    "Your safety is the most important thing."
                ),
                "streamed": False,
                "safety_flagged": True,
                "tokens_used": 0,
            }
        
        # Retrieve context
        rag_context = await self.retrieve_context(session, user_id)
        
        # Build system prompt
        system_prompt = self._build_system_prompt(rag_context)
        
        # Get conversation history if provided
        conversation_history = []
        if conversation_id:
            history = await self._get_conversation_history(session, conversation_id, user_id)
            conversation_history = self._build_conversation_history(history)
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history,
            {"role": "user", "content": message},
        ]
        
        # Call LLM with provider rotation fallback
        last_error = None
        
        # Try primary provider first
        try:
            if stream:
                response = await self._call_llm(messages, max_tokens, stream=False)
                return {
                    **response,
                    "streamed": False,
                }
            else:
                response = await self._call_llm(messages, max_tokens, stream=False)
                return response
        except (LLMServiceError, Exception) as e:
            last_error = e
            self.logger.warning(f"Primary LLM call failed: {e}")
        
        # Try provider pool fallbacks
        if self.provider_pool:
            orig_provider, orig_model, orig_key = self.provider, self.model, self.api_key
            for pool_provider, pool_model in self.provider_pool:
                self.logger.info(f"Trying fallback provider {pool_provider}/{pool_model}")
                try:
                    self.provider = LLMProvider(pool_provider)
                    self.model = pool_model
                    if pool_provider in ("openrouter", "minimax"):
                        self.api_key = self._get_openrouter_key() or orig_key
                    
                    response = await self._call_llm(messages, max_tokens, stream=False)
                    self.provider, self.model, self.api_key = orig_provider, orig_model, orig_key
                    return response
                except (LLMServiceError, Exception) as e2:
                    self.logger.warning(f"Fallback provider {pool_provider}/{pool_model} failed: {e2}")
                    last_error = e2
                    self.provider, self.model, self.api_key = orig_provider, orig_model, orig_key
                    continue
        
        # All providers failed — use rule-based fallback
        self.logger.warning(f"All providers failed, using rule-based fallback: {last_error}")
        return await self._rule_based_response(message, rag_context)
    
    async def _call_llm(self, messages: List[Dict], max_tokens: int, stream: bool) -> Dict[str, Any]:
        """Call the LLM API.
        
        Args:
            messages: List of message objects
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            
        Returns:
            LLM response
        """
        if self.provider == LLMProvider.OPENAI:
            key = self._get_openai_key()
            if not key:
                raise LLMServiceError("No OpenAI API key configured")
            return await self._call_openai(messages, max_tokens, stream)
        elif self.provider == LLMProvider.OPENROUTER:
            key = self._get_openrouter_key()
            if not key:
                raise LLMServiceError("No OpenRouter API key configured")
            return await self._call_openrouter(messages, max_tokens, stream)
        elif self.provider == LLMProvider.MINIMAX:
            key = self._get_openrouter_key()
            if not key:
                raise LLMServiceError("No OpenRouter API key configured")
            return await self._call_minimax(messages, max_tokens, stream)
        else:
            key = self._get_anthropic_key()
            if not key:
                raise LLMServiceError("No Anthropic API key configured")
            return await self._call_anthropic(messages, max_tokens, stream)
    
    async def _call_openai(self, messages: List[Dict], max_tokens: int, stream: bool) -> Dict[str, Any]:
        """Call OpenAI API."""
        api_key = self.api_key or self._get_openai_key()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                        "stream": stream,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                tokens = data["usage"]["total_tokens"]
                
                return {
                    "response": content,
                    "tokens_used": tokens,
                    "model": self.model,
                    "provider": "openai",
                    "streamed": stream,
                    "safety_flagged": False,
                }
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"OpenAI API error: {e.response.text}")
                raise LLMServiceError(f"OpenAI API error: {e.response.text}")
    
    async def _call_anthropic(self, messages: List[Dict], max_tokens: int, stream: bool) -> Dict[str, Any]:
        """Call Anthropic API."""
        api_key = self.api_key or self._get_anthropic_key()
        
        # Convert OpenAI-style messages to Anthropic format
        system_message = None
        formatted_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                payload = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": formatted_messages,
                    "temperature": 0.7,
                }
                
                if system_message:
                    payload["system"] = system_message
                
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                
                content = data["content"][0]["text"]
                tokens = data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
                
                return {
                    "response": content,
                    "tokens_used": tokens,
                    "model": self.model,
                    "provider": "anthropic",
                    "streamed": False,
                    "safety_flagged": False,
                }
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"Anthropic API error: {e}")
                raise LLMServiceError(f"Anthropic API error: {str(e)}")
    
    async def _call_openrouter(self, messages: List[Dict], max_tokens: int, stream: bool) -> Dict[str, Any]:
        """Call OpenRouter API for unified access to multiple models.
        
        OpenRouter provides access to GPT-4o, Claude 3.5, and many other
        models through a single API with unified pricing.
        """
        api_key = self.api_key or self._get_openrouter_key()
        
        # OpenRouter uses same format as OpenAI
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/russell-taylor/T1D-Companion",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                        "stream": stream,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                tokens = data["usage"]["total_tokens"]
                
                return {
                    "response": content,
                    "tokens_used": tokens,
                    "model": self.model,
                    "provider": "openrouter",
                    "streamed": stream,
                    "safety_flagged": False,
                }
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"OpenRouter API error: {e.response.text}")
                raise LLMServiceError(f"OpenRouter API error: {e.response.text}")
    
    async def _call_minimax(self, messages: List[Dict], max_tokens: int, stream: bool) -> Dict[str, Any]:
        """Call MiniMax API via OpenRouter (free tier).
        
        MiniMax M2.5 is a strong open-weight model available
        at no cost through OpenRouter.
        """
        api_key = self.api_key or self._get_openrouter_key()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/russell-taylor/T1D-Companion",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                        "stream": stream,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                tokens = data["usage"]["total_tokens"]
                
                return {
                    "response": content,
                    "tokens_used": tokens,
                    "model": self.model,
                    "provider": "minimax",
                    "streamed": stream,
                    "safety_flagged": False,
                }
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"MiniMax API error: {e.response.text}")
                raise LLMServiceError(f"MiniMax API error: {e.response.text}")
    
    # -------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------
    

    
    async def _get_conversation_history(
        self,
        session: AsyncSession,
        conversation_id: int,
        user_id: int,
        max_turns: int = 10,
    ) -> List[ConversationTurn]:
        """Get conversation history.
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            user_id: User ID
            max_turns: Maximum turns to retrieve
            
        Returns:
            List of conversation turns
        """
        result = await session.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.conversation_id == conversation_id,
                Conversation.conversation_id == ConversationMessage.conversation_id,
                Conversation.user_id == user_id,
            )
            .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
            .order_by(ConversationMessage.timestamp.asc())
            .limit(max_turns * 2)  # Get more to ensure we have both sides
        )
        
        messages = result.scalars().all()
        
        turns = []
        for msg in messages:
            turns.append(ConversationTurn(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
            ))
        
        return turns
    
    def _get_openai_key(self) -> Optional[str]:
        """Get OpenAI API key from environment."""
        import os
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            try:
                from app.config import get_settings
                key = get_settings().openai_api_key
            except Exception:
                pass
        return key  # Can be None - fallback will handle it
    
    def _get_anthropic_key(self) -> Optional[str]:
        """Get Anthropic API key from environment."""
        import os
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            try:
                from app.config import get_settings
                key = get_settings().anthropic_api_key
            except Exception:
                pass
        return key  # Can be None - fallback will handle it
    
    def _get_openrouter_key(self) -> Optional[str]:
        """Get OpenRouter API key from environment or config."""
        import os
        from app.config import get_settings
        
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            try:
                key = get_settings().openrouter_api_key
            except Exception:
                pass
        if not key:
            # Fallback to OpenAI key if available
            key = os.getenv("OPENAI_API_KEY")
        if not key:
            try:
                key = get_settings().openai_api_key
            except Exception:
                pass
        return key  # Can be None - fallback will handle it
    
    # -------------------------------------------------------------------
    # Summarization
    # -------------------------------------------------------------------
    
    async def summarize_patterns(
        self,
        pattern_data: Dict[str, Any],
        user_id: int,
    ) -> str:
        """Summarize pattern data in natural language.
        
        Args:
            pattern_data: Pattern analysis results
            user_id: User ID for context
            
        Returns:
            Natural language summary
        """
        # Extract key points
        tir = pattern_data.get("time_in_range", {})
        spikes = pattern_data.get("post_meal_spikes", {}).get("count", 0)
        overnight = pattern_data.get("overnight_hypoglycemia", {}).get("event_count", 0)
        
        summary_prompt = f"""Write a brief, empathetic summary of these diabetes patterns for a patient:

- Time in target range (70-180 mg/dL): {tir.get('percentage', 0):.1f}%
- Time below range: {tir.get('below_range', {}).get('percentage', 0):.1f}%
- Time above range: {tir.get('above_range', {}).get('percentage', 0):.1f}%
- Post-meal spikes detected: {spikes}
- Overnight lows detected: {overnight}
- Estimated A1C: {pattern_data.get('estimated_a1c', 0)}

Write 2-3 sentences that:
1. Acknowledge the patterns neutrally
2. Suggest one actionable consideration (not a directive)
3. Encourage discussion with their healthcare team

Use supportive tone."""
        
        messages = [
            {"role": "system", "content": "You are a supportive diabetes education assistant."},
            {"role": "user", "content": summary_prompt},
        ]
        
        response = await self._call_llm(messages, max_tokens=300, stream=False)
        return response["response"]


# ---------------------------------------------------------------------------
# Global LLM Service Instance
# ---------------------------------------------------------------------------

_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create global LLM service instance.
    
    Returns:
        LLM service instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def set_llm_service(service: LLMService) -> None:
    """Set global LLM service instance.
    
    Args:
        service: LLM service to use globally
    """
    global _llm_service
    _llm_service = service