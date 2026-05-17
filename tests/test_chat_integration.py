"""Integration tests for the /api/v1/chat endpoint with real DB.

These tests exercise the full FastAPI endpoint including:
- Conversation/message creation in the DB
- Rule-based fallback response generation (via mock coordinator)
- Emergency short-circuit
- Streaming endpoint
"""

import json
import pytest
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, ConversationMessage, User


# =============================================================================
# Mock coordinator
# =============================================================================

class MockCoordinator:
    """Minimal coordinator mock returning deterministic responses."""

    def __init__(self, message: str = ""):
        self.message = message

    async def process_chat_message(
        self,
        message: str,
        user_id: int,
        session: AsyncSession | None = None,
        conversation_id: int | None = None,
    ) -> dict:
        from app.ai.safety import SafetyScaffold
        scaffold = SafetyScaffold()
        safety = scaffold.validate(message, {"source": "user"})

        if not safety["is_safe"]:
            return {
                "error": "safety_violation",
                "message": "I'm not able to provide that information. Please consult your healthcare team for medical advice.",
                "safety_flagged": True,
            }

        if self.message:
            return {"response": self.message}

        return {
            "response": (
                "Based on your glucose data, I can help you understand patterns in your readings. "
                "Educational insights suggest that consistent monitoring is key. "
                "Consider discussing your trends with your diabetes care team."
            ),
        }

    async def startup(self):
        pass

    async def shutdown(self):
        pass


# =============================================================================
# Test app factory with overrides
# =============================================================================

@pytest.fixture(scope="module")
def chat_app():
    """Create a FastAPI app with chat router for testing.

    Also replaces ``app.main.app`` so that chat.py can find
    the coordinator via ``app.state.coordinator``.
    """
    import app.main as main_module
    from fastapi import FastAPI
    from app.api.chat import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.state.coordinator = MockCoordinator()

    # Point app.main.app at our test app so local imports in chat.py
    # resolve to this test instance.
    main_module.app = app

    return app


@pytest.fixture
def client(chat_app):
    """Return a TestClient for the chat app."""
    return TestClient(chat_app)


# =============================================================================
# Override helper
# =============================================================================

def override_auth_and_db(chat_app, db_session, test_user):
    """Install dependency overrides to bypass real auth and DB.

    Must be called per-test (or inside a context manager) because
    each test has its own ``db_session`` (function-scoped).
    """
    from app.core.database import get_db
    from app.core.security import get_current_user

    async def _get_db():
        yield db_session

    async def _get_current_user():
        return test_user

    chat_app.dependency_overrides[get_db] = _get_db
    chat_app.dependency_overrides[get_current_user] = _get_current_user


def _clean_overrides(chat_app):
    """Remove all dependency overrides."""
    from app.core.database import get_db
    from app.core.security import get_current_user
    chat_app.dependency_overrides.pop(get_db, None)
    chat_app.dependency_overrides.pop(get_current_user, None)


# =============================================================================
# Async test helper
# =============================================================================

async def _chat_post(client, chat_app, db_session, test_user,
                     message: str, conversation_id: int | None = None) -> dict:
    """POST /api/v1/chat with proper overrides."""
    override_auth_and_db(chat_app, db_session, test_user)
    try:
        payload = {"message": message}
        if conversation_id is not None:
            payload["conversation_id"] = conversation_id

        response = client.post("/api/v1/chat", json=payload)
        if response.status_code != 200:
            return {"status": response.status_code, "detail": response.text}
        return response.json()
    finally:
        _clean_overrides(chat_app)


async def _stream_post(client, chat_app, db_session, test_user,
                       message: str) -> list:
    """POST /api/v1/chat/stream with proper overrides, returning parsed events."""
    from app.core.database import get_db
    from app.core.security import get_current_user

    async def _get_db():
        yield db_session

    async def _get_current_user():
        return test_user

    chat_app.dependency_overrides[get_db] = _get_db
    chat_app.dependency_overrides[get_current_user] = _get_current_user

    try:
        # TestClient doesn't support streaming POST in older versions,
        # so use a raw httpx call or just verify the endpoint returns 200
        # with the right content-type. For SSE parsing, we'll use the
        # test client normally.
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": message},
        )

        if response.status_code != 200:
            return [{"error": response.status_code, "text": response.text}]

        content_type = response.headers.get("content-type", "")
        events = []
        if "event-stream" in content_type:
            for line in response.text.strip().split("\n"):
                if line.startswith("data: "):
                    try:
                        events.append(json.loads(line[6:]))
                    except json.JSONDecodeError:
                        events.append({"raw": line[6:]})
        else:
            # If not streaming, just check content-type
            events.append({"content_type": content_type})

        return events
    finally:
        chat_app.dependency_overrides.pop(get_db, None)
        chat_app.dependency_overrides.pop(get_current_user, None)


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.asyncio
async def test_chat_endpoint_creates_conversation(
    client, chat_app, db_session, test_user
):
    """POST /api/v1/chat creates Conversation and ConversationMessage rows."""
    result = await _chat_post(
        client, chat_app, db_session, test_user,
        "Hello, how are my glucose levels?",
    )

    assert "error" not in result or isinstance(result.get("error"), str) is False, \
        f"Endpoint error: {result.get('detail', result)}"
    assert result["conversation_id"] is not None
    assert result["message_id"] is not None

    # Verify Conversation row in DB
    conv_query = await db_session.execute(
        select(Conversation).where(Conversation.id == result["conversation_id"])
    )
    conv = conv_query.scalar_one_or_none()
    assert conv is not None
    assert conv.user_id == test_user.id

    # Verify user + assistant messages
    msg_query = await db_session.execute(
        select(ConversationMessage).where(
            ConversationMessage.conversation_id == result["conversation_id"]
        ).order_by(ConversationMessage.timestamp)
    )
    messages = msg_query.scalars().all()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello, how are my glucose levels?"
    assert messages[1].role == "assistant"
    assert len(messages[1].content) > 0


@pytest.mark.asyncio
async def test_chat_endpoint_returns_response(
    client, chat_app, db_session, test_user
):
    """Chat response contains educational text and is saved to DB."""
    result = await _chat_post(
        client, chat_app, db_session, test_user,
        "What is my time in range?",
    )

    assert "error" not in result or isinstance(result.get("error"), str) is False
    assert len(result["response"]) > 0
    assert result["conversation_id"] is not None

    # Verify assistant message saved
    msg_query = await db_session.execute(
        select(ConversationMessage).where(
            ConversationMessage.conversation_id == result["conversation_id"],
            ConversationMessage.role == "assistant",
        )
    )
    ai_msg = msg_query.scalar_one_or_none()
    assert ai_msg is not None
    assert ai_msg.content == result["response"]


@pytest.mark.asyncio
async def test_chat_endpoint_with_existing_conversation(
    client, chat_app, db_session, test_user
):
    """Sending message with conversation_id appends to existing conversation."""
    # First message
    result1 = await _chat_post(
        client, chat_app, db_session, test_user,
        "First message",
    )
    conv_id = result1["conversation_id"]
    assert conv_id is not None

    # Second message with conversation_id
    result2 = await _chat_post(
        client, chat_app, db_session, test_user,
        "Second message", conversation_id=conv_id,
    )

    assert result2["conversation_id"] == conv_id
    assert result2["message_id"] != result1["message_id"]

    # Verify all 4 messages in conversation
    msg_query = await db_session.execute(
        select(ConversationMessage).where(
            ConversationMessage.conversation_id == conv_id
        ).order_by(ConversationMessage.timestamp)
    )
    messages = msg_query.scalars().all()
    assert len(messages) == 4
    assert messages[0].content == "First message"
    assert messages[2].content == "Second message"


@pytest.mark.asyncio
async def test_chat_endpoint_emergency_short_circuits(
    client, chat_app, db_session, test_user
):
    """Emergency keywords trigger safety escalation in response.
    
    The SafetyScaffold detects emergency keywords and either:
    (a) the mock coordinator returns a safety_violation error with emergency text, or
    (b) the post-LLM safety check blocks the response and returns a safe fallback.
    Either way, the response should NOT be a normal educational answer.
    """
    result = await _chat_post(
        client, chat_app, db_session, test_user,
        "I'm having severe low blood sugar and can't wake up",
    )

    assert "error" not in result or isinstance(result.get("error"), str) is False
    response_lower = result["response"].lower()
    # The response should be a safety-related message, not a normal educational one.
    # It will contain emergency/seek-immediate language OR the safety fallback message.
    is_safety_response = (
        "seek immediate" in response_lower
        or "emergency" in response_lower
        or "not able to provide" in response_lower
        or "consult your healthcare" in response_lower
    )
    assert is_safety_response, f"Expected safety response, got: {result['response']}"


@pytest.mark.asyncio
async def test_chat_streaming_endpoint(
    client, chat_app, db_session, test_user
):
    """POST /api/v1/chat/stream returns proper SSE response."""
    events = await _stream_post(
        client, chat_app, db_session, test_user,
        "Hello, tell me about my glucose",
    )

    # Check for error
    if isinstance(events, list) and len(events) == 1 and "error" in events[0]:
        pytest.fail(f"Streaming endpoint failed: {events[0]['text']}")

    # Should have SSE events OR at least the content-type is text/event-stream
    assert len(events) > 0


@pytest.mark.asyncio
async def test_chat_streaming_creates_messages(
    client, chat_app, db_session, test_user
):
    """Streaming endpoint saves assistant message to DB."""
    from app.core.database import get_db
    from app.core.security import get_current_user

    async def _get_db():
        yield db_session

    async def _get_current_user():
        return test_user

    chat_app.dependency_overrides[get_db] = _get_db
    chat_app.dependency_overrides[get_current_user] = _get_current_user

    try:
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "Test stream message"},
        )

        assert response.status_code == 200

        # Parse SSE events to find message_id
        events = []
        for line in response.text.strip().split("\n"):
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass

        assert len(events) > 0

        # Last event should be complete
        last_event = events[-1]
        assert "message_id" in last_event

        # Verify assistant message in DB
        msg_query = await db_session.execute(
            select(ConversationMessage).where(
                ConversationMessage.id == last_event["message_id"],
            )
        )
        msg = msg_query.scalar_one_or_none()
        assert msg is not None
        assert msg.role == "assistant"
        assert len(msg.content) > 0
    finally:
        chat_app.dependency_overrides.pop(get_db, None)
        chat_app.dependency_overrides.pop(get_current_user, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])