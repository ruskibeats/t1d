"""Agent coordinator for T1D Companion.

This module manages the multi-agent system, delegating tasks to specialized agents
for data ingestion, pattern analysis, conversation, and safety monitoring.
"""

import re
from typing import Any

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AgentCoordinator:
    """Coordinates specialized agents for T1D data analysis and conversation.

    This class manages the multi-agent system that handles:
    - Data ingestion from CGM and meal trackers
    - Pattern detection and analysis
    - Natural language conversation
    - Safety monitoring and escalation

    Note: This is a lightweight coordinator. In a production system with
    pi-subagents, these would be separate processes. Here we use a simplified
    in-process approach for the Python backend.
    """

    def __init__(self):
        """Initialize the agent coordinator."""
        self.agents: dict[str, Any] = {}
        self.is_running = False
        self.logger = get_logger(self.__class__.__name__)

    async def startup(self) -> None:
        """Initialize all specialized agents."""
        self.logger.info("Starting agent coordinator...")

        # Initialize agent stubs
        self.agents = {
            "data_ingestion": DataIngestionAgent(),
            "pattern": PatternAgent(),
            "conversation": ConversationAgent(),
            "safety": SafetyAgent(),
            "summary": SummaryAgent(),
        }

        self.is_running = True
        self.logger.info("All agents started successfully")

    async def shutdown(self) -> None:
        """Shutdown all agents."""
        self.logger.info("Shutting down agent coordinator...")

        for name, agent in self.agents.items():
            try:
                if hasattr(agent, "shutdown"):
                    await agent.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down {name}: {e}")

        self.is_running = False
        self.logger.info("Agent coordinator stopped")

    async def delegate_task(self, task_type: str, data: dict) -> dict:
        """Delegate a task to the appropriate agent.

        Args:
            task_type: Type of task to delegate
            data: Task-specific data

        Returns:
            Dict: Task result

        Raises:
            ValueError: If task_type is unknown
        """
        if not self.is_running:
            raise RuntimeError("Agent coordinator is not running")

        agent_map = {
            "ingest": self.agents["data_ingestion"],
            "pattern": self.agents["pattern"],
            "converse": self.agents["conversation"],
            "safety_check": self.agents["safety"],
            "summarize": self.agents["summary"],
        }

        if task_type not in agent_map:
            raise ValueError(f"Unknown task type: {task_type}")

        agent = agent_map[task_type]
        self.logger.debug(f"Delegating {task_type} to {agent.__class__.__name__}")

        return await agent.handle(data)

    async def process_chat_message(
        self,
        message: str,
        user_id: int,
        session,
        conversation_id: int | None = None,
    ) -> dict:
        """Process a chat message through the full agent pipeline.

        Args:
            message: User message
            user_id: User ID
            session: Database session (AsyncSession)
            conversation_id: Optional conversation ID

        Returns:
            Dict: Response with agent analysis
        """
        # First, safety check
        safety_result = await self.agents["safety"].handle({
            "content": message,
            "content_type": "user_message",
            "user_id": user_id,
        })

        if not safety_result.get("is_safe", False):
            return {
                "error": "safety_violation",
                "message": safety_result.get("message", "Content flagged by safety filters."),
                "safety_result": safety_result,
            }

        # Get relevant context (glucose data, events, patterns)
        context = await self.agents["data_ingestion"].handle({
            "action": "get_context",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "session": session,
        })

        # Analyze for patterns
        pattern_result = await self.agents["pattern"].handle({
            "action": "analyze_for_conversation",
            "user_id": user_id,
            "context": context,
            "message": message,
            "session": session,
        })

        # Generate response
        response = await self.agents["conversation"].handle({
            "message": message,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "context": context,
            "patterns": pattern_result,
            "safety_result": safety_result,
            "session": session,
        })

        # Post-LLM safety validation: check the assistant response before returning
        response_text = response.get("response", "")
        if response_text:
            post_safety = await self.agents["safety"].handle({
                "content": response_text,
                "content_type": "assistant_response",
                "user_id": user_id,
            })

            if not post_safety.get("is_safe", True):
                self.logger.warning(
                    f"Post-LLM safety check blocked response for user {user_id}: "
                    f"{post_safety.get('reasons', [])}"
                )
                response["response"] = (
                    "I'm not able to provide that information. "
                    "Please consult your healthcare team for medical advice."
                )
                response["safety_flagged"] = True
                response["post_safety_result"] = post_safety
            else:
                # Disclaimer enforcement: ensure long responses include educational disclaimer
                DISCLAIMERS = [
                    "educational insight",
                    "educational information",
                    "not medical advice",
                    "consider discussing",
                    "consult your health",
                    "consult your diabetes",
                    "discuss with your",
                ]
                if len(response_text) > 200 and not any(
                    d in response_text.lower() for d in DISCLAIMERS
                ):
                    response["response"] = response_text.rstrip() + (
                        "\n\n---\n"
                        "*This is educational information, not medical advice. "
                        "Consider discussing these patterns with your healthcare team.*"
                    )
                    response["disclaimer_appended"] = True

        # Add metadata
        response["metadata"] = {
            "safety_checked": True,
            "patterns_analyzed": True,
            "context_included": bool(context),
        }

        return response


class BaseAgent:
    """Base class for all specialized agents."""

    def __init__(self, name: str):
        """Initialize base agent.

        Args:
            name: Agent name for logging
        """
        self.name = name
        self.logger = get_logger(f"agents.{name}")

    async def handle(self, data: dict) -> dict:
        """Handle a task.

        Args:
            data: Task data

        Returns:
            Dict: Task result
        """
        raise NotImplementedError(f"{self.name} must implement handle()")

    async def shutdown(self) -> None:
        """Shutdown agent resources."""
        pass


class DataIngestionAgent(BaseAgent):
    """Agent for handling CGM and meal tracker data ingestion."""

    def __init__(self):
        super().__init__("data_ingestion")

    async def handle(self, data: dict) -> dict:
        """Handle data ingestion tasks.

        Delegates to LLMService.retrieve_context() to get real glucose
        readings, events, and pattern summaries from the database.

        Args:
            data: Task data with 'action' key and 'session' for DB access

        Returns:
            Dict: Context data with glucose, events, patterns, and user profile
        """
        action = data.get("action")

        if action == "get_context":
            session = data.get("session")
            user_id = data["user_id"]

            if not session:
                self.logger.warning("No session provided to DataIngestionAgent")
                return {
                    "glucose": {"recent_count": 0, "latest_value": None, "trend": None},
                    "events": [],
                    "patterns": [],
                    "user_profile": None,
                    "error": "no session",
                }

            try:
                from app.services.llm_service import get_llm_service
                llm_service = get_llm_service()
                rag_context = await llm_service.retrieve_context(session, user_id)
                return {
                    "glucose": {
                        "recent_count": len(rag_context.recent_glucose),
                        "latest_value": rag_context.recent_glucose[0]["value"] if rag_context.recent_glucose else None,
                        "trend": rag_context.recent_glucose[0].get("trend") if rag_context.recent_glucose else None,
                        "readings": rag_context.recent_glucose,
                    },
                    "events": rag_context.recent_events,
                    "patterns": rag_context.pattern_summary,
                    "graph_edges": rag_context.graph_edges,
                    "user_profile": rag_context.user_profile,
                }
            except Exception as e:
                self.logger.error(f"Data ingestion failed: {e}")
                return {
                    "glucose": {"recent_count": 0, "latest_value": None, "trend": None},
                    "events": [],
                    "patterns": [],
                    "user_profile": None,
                    "error": str(e),
                }

        return {"status": "ok", "action": action}


class PatternAgent(BaseAgent):
    """Agent for detecting and analyzing glucose patterns."""

    def __init__(self):
        super().__init__("pattern")

    async def handle(self, data: dict) -> dict:
        """Handle pattern analysis tasks.

        Delegates to PatternService for time-in-range, spike detection,
        and overnight hypoglycemia analysis.

        Args:
            data: Task data with 'action' key and 'session' for DB access

        Returns:
            Dict: Analysis results with TIR, spikes, overnight lows
        """
        action = data.get("action")

        if action == "analyze_for_conversation":
            session = data.get("session")
            user_id = data["user_id"]

            if not session:
                self.logger.warning("No session provided to PatternAgent")
                return {
                    "patterns": [],
                    "trends": {},
                    "correlations": [],
                    "tir_percentage": 0,
                    "estimated_a1c": 0,
                    "spike_count": 0,
                    "overnight_low_count": 0,
                    "error": "no session",
                }

            try:
                from app.services.pattern_service import PatternService
                from datetime import datetime, timedelta, timezone

                pattern_service = PatternService()
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=14)

                # Calculate TIR
                tir = await pattern_service.calculate_time_in_range(
                    session, user_id, start_date, end_date
                )

                # Detect spikes
                spikes = await pattern_service.detect_post_meal_spikes(
                    session, user_id, start_date, end_date
                )

                # Detect overnight lows
                overnight = await pattern_service.detect_overnight_hypoglycemia(
                    session, user_id, start_date, end_date
                )

                tir_percentage = tir.get("time_in_range", {}).get("percentage", 0)
                estimated_a1c = tir.get("estimated_a1c", 0)

                return {
                    "patterns": {
                        "time_in_range": tir,
                        "post_meal_spikes": {"count": len(spikes), "spikes": spikes[:3]},
                        "overnight_hypoglycemia": {"count": len(overnight), "events": overnight[:3]},
                    },
                    "tir_percentage": tir_percentage,
                    "estimated_a1c": estimated_a1c,
                    "spike_count": len(spikes),
                    "overnight_low_count": len(overnight),
                    "tir": tir,
                    "spikes": spikes[:3],
                    "overnight_lows": overnight[:3],
                }
            except Exception as e:
                self.logger.error(f"Pattern analysis failed: {e}")
                return {
                    "patterns": [],
                    "trends": {},
                    "correlations": [],
                    "tir_percentage": 0,
                    "estimated_a1c": 0,
                    "spike_count": 0,
                    "overnight_low_count": 0,
                    "error": str(e),
                }

        return {"status": "ok", "action": action}


class ConversationAgent(BaseAgent):
    """Agent for natural language conversation."""

    def __init__(self):
        super().__init__("conversation")

    async def handle(self, data: dict) -> dict:
        """Handle conversation tasks.

        Delegates to LLMService.generate_response() for real LLM-powered
        responses grounded in user data and patterns.

        Args:
            data: Task data with message, user_id, session, context, patterns

        Returns:
            Dict: Response with generated text, confidence, sources
        """
        message = data.get("message", "")
        user_id = data.get("user_id")
        session = data.get("session")

        if not session:
            return {
                "response": "I need a database session to generate a response.",
                "confidence": 0,
                "sources": [],
            }

        try:
            from app.services.llm_service import get_llm_service
            llm_service = get_llm_service()

            llm_response = await llm_service.generate_response(
                message=message,
                session=session,
                user_id=user_id,
                stream=False,
            )
            return {
                "response": llm_response.get("response", ""),
                "confidence": 0.8,
                "sources": ["glucose_history", "context_events", "pattern_analysis"],
                "tokens_used": llm_response.get("tokens_used", 0),
                "provider": llm_response.get("provider", "unknown"),
            }
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            return {
                "response": (
                    "I'm having trouble generating a response right now. "
                    "Please try again in a moment."
                ),
                "confidence": 0,
                "sources": [],
                "error": str(e),
            }


class SafetyAgent(BaseAgent):
    """Agent for safety monitoring and content filtering.

    Delegates all detection logic to SafetyScaffold to avoid
    duplicating keyword lists and violation patterns.
    """

    def __init__(self):
        super().__init__("safety")
        from app.ai.safety import SafetyScaffold
        self._scaffold = SafetyScaffold()

    async def handle(self, data: dict) -> dict:
        """Handle safety check tasks.

        Delegates to SafetyScaffold for all detection logic.

        Args:
            data: Task data with content to check

        Returns:
            Dict: Safety check result
        """
        content = data.get("content", "")
        content_type = data.get("content_type", "unknown")

        # Use SafetyScaffold as the single source of truth
        result = self._scaffold.validate(
            content,
            context={"source": "assistant" if content_type == "assistant_response" else "user"}
        )

        is_safe = result["is_safe"]
        requires_escalation = result["requires_escalation"]
        reasons = result["reasons"]
        matched_conditions = result["matched_conditions"]

        if requires_escalation or not is_safe:
            self.logger.warning(
                f"Safety alert: {matched_conditions} "
                f"detected in {content_type}: {reasons}"
            )

        # Build response matching the original SafetyAgent interface
        if requires_escalation:
            safety_level = "emergency"
            message = (
                "Please seek immediate medical attention or call emergency services. "
                "Your safety is our priority."
            )
        elif not is_safe:
            safety_level = "blocked"
            message = (
                "I'm not able to provide that information. "
                "Please consult your healthcare team for medical advice."
            )
        else:
            safety_level = "safe"
            message = "Content passed safety check"

        return {
            "is_safe": is_safe,
            "safety_level": safety_level,
            "reasons": reasons,
            "requires_escalation": requires_escalation,
            "matched_conditions": matched_conditions,
            "message": message,
            "scaffold_result": result,
        }


class SummaryAgent(BaseAgent):
    """Agent for generating summaries and reports."""

    def __init__(self):
        super().__init__("summary")

    async def handle(self, data: dict) -> dict:
        """Handle summary generation tasks.

        Tries LLM-based summarization first, falls back to rule-based
        summary generated from pattern data.

        Args:
            data: Task data with format, patterns, user_id, session

        Returns:
            Dict: Summary result with status, format, and summary text
        """
        format_type = data.get("format", "text")
        pattern_data = data.get("patterns", {})
        user_id = data.get("user_id")
        session = data.get("session")

        if not session or not pattern_data:
            return {
                "status": "ok",
                "format": format_type,
                "summary": "No pattern data available for summary.",
            }

        try:
            from app.services.llm_service import get_llm_service
            llm_service = get_llm_service()

            summary = await llm_service.summarize_patterns(pattern_data, user_id)
            return {
                "status": "ok",
                "format": format_type,
                "summary": summary,
            }
        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}")
            # Fallback: generate a basic summary from pattern data
            tir = pattern_data.get("time_in_range", {}).get("percentage", 0)
            spikes = pattern_data.get("post_meal_spikes", {}).get("count", 0)
            overnight = pattern_data.get("overnight_hypoglycemia", {}).get("count", 0)
            a1c = pattern_data.get("estimated_a1c", 0)

            return {
                "status": "ok",
                "format": format_type,
                "summary": (
                    f"Over the last 14 days, your time in range was {tir:.1f}%, "
                    f"with {spikes} post-meal spikes and {overnight} overnight low events. "
                    f"Your estimated A1C is {a1c}."
                ),
            }
