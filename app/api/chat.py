"""Conversational AI API endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import Conversation as ConversationModel
from app.db.models import ConversationMessage as ConversationMessageModel
from app.db.models import User
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    SafetyCheck,
    SafetyCheckRequest,
    StreamingChunk,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> ChatResponse:
    """Chat with AI assistant about diabetes data and patterns.
    
    Args:
        request: Chat request with user message
        session: Database session
        user: Current authenticated user
        
    Returns:
        ChatResponse: AI response
    """
    from datetime import datetime, timedelta, timezone

    # Get or create conversation
    conversation = None
    if request.conversation_id:
        result = await session.execute(
            select(ConversationModel).where(
                ConversationModel.id == request.conversation_id,
                ConversationModel.user_id == user.id,
            )
        )
        conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = ConversationModel(
            user_id=user.id,
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

    # Save user message
    user_message = ConversationMessageModel(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    session.add(user_message)
    await session.commit()
    await session.refresh(user_message)

    # Build context with glucose, events, AND patterns
    context = await _build_context(session, user, request)

    # Call the real agent coordinator pipeline
    from app.agents.coordinator import AgentCoordinator
    from app.main import app as fastapi_app

    coordinator = getattr(fastapi_app.state, 'coordinator', None)

    if coordinator:
        try:
            ai_result = await coordinator.process_chat_message(
                message=request.message,
                user_id=user.id,
                session=session,
                conversation_id=conversation.id,
            )

            if "error" in ai_result:
                ai_response_text = ai_result.get("message", "An error occurred.")
            else:
                ai_response_text = ai_result.get("response", "")

            # Second safety layer: SafetyScaffold post-LLM check
            if ai_response_text:
                from app.ai.safety import SafetyScaffold
                scaffold = SafetyScaffold()
                safety = scaffold.validate(ai_response_text, {"source": "assistant"})
                if not safety["is_safe"]:
                    logger.warning(
                        f"SafetyScaffold blocked AI response for user {user.id}: "
                        f"{safety.get('reasons', [])}"
                    )
                    ai_response_text = (
                        "I'm not able to provide that information. "
                        "Please consult your healthcare team for medical advice."
                    )
        except Exception as e:
            logger.error(f"Agent coordinator failed: {e}")
            ai_response_text = (
                "I'm having trouble processing your request right now. "
                "Please try again in a moment."
            )
    else:
        logger.warning("Agent coordinator not available on app.state")
        ai_response_text = (
            "The AI assistant is not available right now. "
            "Please try again later."
        )

    # Save AI response
    ai_message = ConversationMessageModel(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response_text,
        extra_data={"context_used": context.get("summary", {})} if context else None,
    )
    session.add(ai_message)

    # Update conversation
    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(ai_message)
    await session.refresh(conversation)

    return ChatResponse(
        response=ai_response_text,
        conversation_id=conversation.id,
        message_id=ai_message.id,
        timestamp=ai_message.timestamp,
        context_used=context,
        sources=["glucose_history", "context_events", "pattern_analysis"] if context else [],
        streaming=False,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> StreamingResponse:
    """Stream chat response.
    
    Args:
        request: Chat request
        session: Database session
        user: Current authenticated user
        
    Returns:
        StreamingResponse: Streaming response
    """
    async def generate():
        from datetime import datetime, timedelta, timezone
        from app.agents.coordinator import AgentCoordinator
        from app.main import app as fastapi_app

        # Get or create conversation
        conversation = None
        if request.conversation_id:
            result = await session.execute(
                select(ConversationModel).where(
                    ConversationModel.id == request.conversation_id,
                    ConversationModel.user_id == user.id,
                )
            )
            conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = ConversationModel(
                user_id=user.id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

        # Save user message
        user_message = ConversationMessageModel(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
        )
        session.add(user_message)
        await session.commit()
        await session.refresh(user_message)

        # Build context with patterns
        context = await _build_context(session, user, request)

        # Call coordinator (block, then stream word-by-word)
        coordinator = getattr(fastapi_app.state, 'coordinator', None)
        response_text = ""

        if coordinator:
            try:
                ai_result = await coordinator.process_chat_message(
                    message=request.message,
                    user_id=user.id,
                    session=session,
                    conversation_id=conversation.id,
                )
                response_text = ai_result.get("response", "")
            except Exception as e:
                logger.error(f"Agent coordinator failed in stream: {e}")
                response_text = "I'm having trouble processing your request right now."
        else:
            response_text = "The AI assistant is not available right now."

        # Save complete AI response before streaming so chunks use the real DB id.
        response_text_str = response_text.strip()

        # Post-LLM safety check before saving/streaming
        from app.ai.safety import SafetyScaffold
        scaffold = SafetyScaffold()
        safety = scaffold.validate(response_text_str, {"source": "assistant"})
        if not safety["is_safe"]:
            logger.warning(
                f"SafetyScaffold blocked stream response for user {user.id}: "
                f"{safety.get('reasons', [])}"
            )
            response_text_str = (
                "I'm not able to provide that information. "
                "Please consult your healthcare team for medical advice."
            )
        elif len(response_text_str) > 200:
            # Ensure disclaimer on long responses
            DISCLAIMERS = ["educational", "not medical", "consult your", "discuss with"]
            if not any(d in response_text_str.lower() for d in DISCLAIMERS):
                response_text_str = response_text_str.rstrip() + (
                    "\n\n---\n"
                    "*This is educational information, not medical advice. "
                    "Consider discussing these patterns with your healthcare team.*"
                )

        ai_message = ConversationMessageModel(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text_str,
            extra_data={"context_used": context.get("summary", {}), "streamed": True},
        )
        session.add(ai_message)
        conversation.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(ai_message)

        # Stream word-by-word
        words = response_text_str.split()
        for i, word in enumerate(words):
            chunk = StreamingChunk(
                chunk=word + " ",
                conversation_id=conversation.id,
                message_id=ai_message.id,
                is_complete=(i == len(words) - 1),
            )
            yield f"data: {chunk.model_dump_json()}\n\n"
            await asyncio.sleep(0.05)

        # Send final completion message
        final_chunk = StreamingChunk(
            chunk="",
            conversation_id=conversation.id,
            message_id=ai_message.id,
            is_complete=True,
        )
        yield f"data: {final_chunk.model_dump_json()}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/conversations", response_model=list[ConversationResponse])
async def get_conversations(
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> list[ConversationResponse]:
    """Get conversation history."""
    result = await session.execute(
        select(ConversationModel)
        .where(ConversationModel.user_id == user.id)
        .offset(skip)
        .limit(limit)
        .order_by(ConversationModel.updated_at.desc())
    )
    conversations = result.scalars().all()
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> ConversationResponse:
    """Get specific conversation."""
    result = await session.execute(
        select(ConversationModel).where(
            ConversationModel.id == conversation_id,
            ConversationModel.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse.model_validate(conversation)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
):
    """Get messages from conversation."""
    result = await session.execute(
        select(ConversationModel).where(
            ConversationModel.id == conversation_id,
            ConversationModel.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await session.execute(
        select(ConversationMessageModel)
        .where(ConversationMessageModel.conversation_id == conversation_id)
        .offset(skip)
        .limit(limit)
        .order_by(ConversationMessageModel.timestamp)
    )
    messages = result.scalars().all()
    from app.models.chat import ChatMessageResponse
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.post("/safety/check")
async def check_safety(
    request: SafetyCheckRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> SafetyCheck:
    """Check content for safety issues."""
    from app.ai.safety import SafetyScaffold
    scaffold = SafetyScaffold()
    result = scaffold.validate(request.content, {"source": "user"})
    return SafetyCheck(
        is_safe=result["is_safe"],
        safety_level=result["safety_level"],
        reasons=result.get("reasons"),
        requires_moderation=result["requires_escalation"],
    )


async def _build_context(session, user, request):
    """Build context for AI response including glucose, events, and patterns."""
    from datetime import datetime, timedelta, timezone
    from app.db.models import ContextEvent, GlucoseReading

    context = {
        "user_profile": {
            "timezone": user.timezone,
            "diabetes_type": user.diabetes_type,
            "target_range": f"{user.target_range_low}-{user.target_range_high} mg/dL",
        },
        "recent_glucose": {},
        "recent_events": [],
        "summary": {},
    }

    # Get recent glucose data
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await session.execute(
        select(GlucoseReading)
        .where(
            GlucoseReading.user_id == user.id,
            GlucoseReading.timestamp >= cutoff,
        )
        .order_by(GlucoseReading.timestamp.desc())
        .limit(20)
    )
    readings = result.scalars().all()

    if readings:
        import statistics
        values = [r.glucose_value for r in readings]
        context["recent_glucose"] = {
            "count": len(readings),
            "latest": readings[0].glucose_value,
            "average": round(statistics.mean(values), 1) if values else 0,
            "min": min(values),
            "max": max(values),
            "range": f"{min(values)}-{max(values)} mg/dL",
        }

    # Get recent events
    cutoff_events = datetime.now(timezone.utc) - timedelta(days=14)
    result = await session.execute(
        select(ContextEvent)
        .where(
            ContextEvent.user_id == user.id,
            ContextEvent.timestamp >= cutoff_events,
        )
        .order_by(ContextEvent.timestamp.desc())
        .limit(20)
    )
    events = result.scalars().all()
    context["recent_events"] = [
        {
            "type": e.event_type,
            "timestamp": e.timestamp.isoformat(),
            "description": e.description or e.event_type,
            "carbs_grams": e.carbs_grams,
            "insulin_units": e.insulin_units,
        }
        for e in events
    ]

    # Get pattern analysis
    from app.services.pattern_service import PatternService
    pattern_service = PatternService()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=14)

    try:
        tir = await pattern_service.calculate_time_in_range(
            session, user.id, start_date, end_date
        )
        spikes = await pattern_service.detect_post_meal_spikes(
            session, user.id, start_date, end_date
        )
        overnight = await pattern_service.detect_overnight_hypoglycemia(
            session, user.id, start_date, end_date
        )
        context["pattern_summary"] = {
            "time_in_range_pct": tir.get("time_in_range", {}).get("percentage", 0),
            "estimated_a1c": tir.get("estimated_a1c", 0),
            "post_meal_spike_count": len(spikes),
            "overnight_low_count": len(overnight),
            "grade": tir.get("grade", "N/A"),
        }
        context["summary"] = context["pattern_summary"]
    except Exception as e:
        logger.warning(f"Pattern analysis failed in chat context: {e}")
        context["pattern_summary"] = None

    return context


# ---------------------------------------------------------------------------
# LLM-Specific Endpoints
# ---------------------------------------------------------------------------

@router.post("/summarize-patterns")
async def summarize_patterns_endpoint(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    """Get natural language summary of user's patterns."""
    from datetime import datetime, timedelta, timezone
    from app.services.pattern_service import PatternService
    from app.services.llm_service import get_llm_service

    pattern_service = PatternService()
    llm = get_llm_service()

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=14)

    pattern_data = await pattern_service.calculate_time_in_range(
        session, user.id, start_date, end_date
    )
    spikes = await pattern_service.detect_post_meal_spikes(
        session, user.id, start_date, end_date
    )
    pattern_data["post_meal_spikes"] = {"count": len(spikes)}

    summary = await llm.summarize_patterns(pattern_data, user.id)

    return {
        "summary": summary,
        "patterns": {
            "time_in_range_pct": pattern_data["time_in_range"]["percentage"],
            "estimated_a1c": pattern_data["estimated_a1c"],
            "spike_count": len(spikes),
        },
    }


@router.post("/analyze-query")
async def analyze_user_query(
    message: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    """Analyze a natural language query about user's data."""
    from app.services.llm_service import get_llm_service

    llm = get_llm_service()
    llm_response = await llm.generate_response(
        message=message,
        session=session,
        user_id=user.id,
        stream=False,
    )

    return {
        "response": llm_response["response"],
        "metadata": {
            "provider": llm_response.get("provider"),
            "tokens_used": llm_response.get("tokens_used"),
            "model": llm_response.get("model"),
        },
    }
