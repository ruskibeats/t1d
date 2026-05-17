---
name: phase1-integration-tests
description: Writes integration tests for the T1D Companion chat pipeline. Tests the full flow: register, login, chat, safety checks, emergency escalation. Uses mocked LLM provider. Use when implementing Phase 1 integration tests.
model: openai/gpt-oss-120b:free
context: fork
---

# Phase 1: Chat Pipeline Integration Tests

## Task

Write `tests/test_chat_pipeline.py` — integration tests for the full chat pipeline. Tests must work WITHOUT a real database (use SQLite in-memory) and WITHOUT a real LLM provider (mock the LLM calls).

## Files to Create

- `tests/test_chat_pipeline.py` — the main test file
- `tests/conftest.py` — shared fixtures (if not already existing)

## Test Infrastructure

### Database Setup

Use SQLite in-memory for tests:

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    from app.db.base import Base
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()
```

### User Fixture

```python
@pytest_asyncio.fixture
async def test_user(db_session):
    from app.core.security import get_password_hash
    from app.db.models import User
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_verified=True,
        diabetes_type="Type 1",
        target_range_low=70,
        target_range_high=180,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
```

### Glucose Data Fixture

```python
@pytest_asyncio.fixture
async def glucose_readings(db_session, test_user):
    from app.db.models import GlucoseReading
    from datetime import datetime, timedelta, timezone
    readings = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=24)
    values = [120, 135, 160, 180, 200, 190, 170, 150, 140, 130,
              125, 118, 110, 105, 100, 95, 90, 88, 85, 82]
    for i, val in enumerate(values):
        reading = GlucoseReading(
            user_id=test_user.id,
            glucose_value=val,
            glucose_units="mg/dL",
            timestamp=base_time + timedelta(minutes=i * 30),
            reading_type="sensor",
            source="manual",
            trend="flat",
        )
        readings.append(reading)
    for r in readings:
        db_session.add(r)
    await db_session.commit()
    return readings
```

### Events Fixture

```python
@pytest_asyncio.fixture
async def context_events(db_session, test_user):
    from app.db.models import ContextEvent
    from datetime import datetime, timedelta, timezone
    events = [
        ContextEvent(
            user_id=test_user.id,
            event_type="meal",
            event_subtype="dinner",
            description="Pasta with sauce",
            carbs_grams=65,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3),
        ),
        ContextEvent(
            user_id=test_user.id,
            event_type="meal",
            event_subtype="breakfast",
            description="Oatmeal with berries",
            carbs_grams=45,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=10),
        ),
        ContextEvent(
            user_id=test_user.id,
            event_type="insulin",
            insulin_units=4.0,
            insulin_type="rapid",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3, minutes=15),
        ),
    ]
    for e in events:
        db_session.add(e)
    await db_session.commit()
    return events
```

## Required Tests

### Test 1: Basic Chat Flow
```python
@pytest.mark.asyncio
async def test_basic_chat_flow(db_session, test_user, glucose_readings, context_events):
    """Test that a user can send a chat message and get a response."""
    from app.agents.coordinator import AgentCoordinator
    
    coordinator = AgentCoordinator()
    await coordinator.startup()
    
    result = await coordinator.process_chat_message(
        message="What's my glucose looking like?",
        user_id=test_user.id,
        session=db_session,
    )
    
    assert "response" in result
    assert len(result["response"]) > 0
    assert result["metadata"]["safety_checked"] is True
    assert result["metadata"]["patterns_analyzed"] is True
```

### Test 2: Safety Check Blocks Emergency
```python
@pytest.mark.asyncio
async def test_emergency_keyword_triggers_escalation(db_session, test_user):
    """Test that emergency keywords trigger safety escalation."""
    from app.agents.coordinator import AgentCoordinator
    
    coordinator = AgentCoordinator()
    await coordinator.startup()
    
    result = await coordinator.process_chat_message(
        message="I'm having a severe low and can't wake up",
        user_id=test_user.id,
        session=db_session,
    )
    
    assert "error" in result
    assert result["error"] == "safety_violation"
```

### Test 3: Pattern Analysis Includes TIR
```python
@pytest.mark.asyncio
async def test_pattern_analysis_includes_tir(db_session, test_user, glucose_readings):
    """Test that pattern analysis calculates time in range."""
    from app.agents.coordinator import AgentCoordinator
    
    coordinator = AgentCoordinator()
    await coordinator.startup()
    
    result = await coordinator.process_chat_message(
        message="What are my patterns?",
        user_id=test_user.id,
        session=db_session,
    )
    
    assert "response" in result
    # The response should contain some reference to the data
    assert result["metadata"]["patterns_analyzed"] is True
```

### Test 4: Conversation Persistence
```python
@pytest.mark.asyncio
async def test_conversation_messages_persisted(db_session, test_user):
    """Test that chat messages are saved to the database."""
    from app.agents.coordinator import AgentCoordinator
    from app.db.models import ConversationMessage
    from sqlalchemy import select, func
    
    coordinator = AgentCoordinator()
    await coordinator.startup()
    
    result = await coordinator.process_chat_message(
        message="Hello, what can you help me with?",
        user_id=test_user.id,
        session=db_session,
    )
    
    # Check that messages were saved
    count = await db_session.execute(
        select(func.count()).select_from(ConversationMessage)
        .where(ConversationMessage.conversation_id == result.get("conversation_id", 0))
    )
    msg_count = count.scalar()
    assert msg_count >= 2  # User message + AI response
```

### Test 5: Meal-Related Query Uses Event Data
```python
@pytest.mark.asyncio
async def test_meal_query_uses_event_data(db_session, test_user, context_events):
    """Test that meal-related queries reference logged meal events."""
    from app.agents.coordinator import AgentCoordinator
    
    coordinator = AgentCoordinator()
    await coordinator.startup()
    
    result = await coordinator.process_chat_message(
        message="What did I eat recently?",
        user_id=test_user.id,
        session=db_session,
    )
    
    assert "response" in result
    response = result["response"].lower()
    # Should reference meal data
    assert "meal" in response or "carbs" in response or "logged" in response
```

### Test 6: Coordinator Delegate Task Routing
```python
@pytest.mark.asyncio
async def test_delegate_task_routing(db_session, test_user):
    """Test that delegate_task routes to the correct agent."""
    from app.agents.coordinator import AgentCoordinator
    
    coordinator = AgentCoordinator()
    await coordinator.startup()
    
    # Test safety routing
    result = await coordinator.delegate_task("safety_check", {
        "content": "hello",
        "content_type": "user_message",
    })
    assert "is_safe" in result
    
    # Test pattern routing
    result = await coordinator.delegate_task("pattern", {
        "action": "analyze_for_conversation",
        "user_id": test_user.id,
        "session": db_session,
    })
    assert "patterns" in result or "tir_percentage" in result
    
    # Test unknown task type
    with pytest.raises(ValueError):
        await coordinator.delegate_task("unknown_task", {})
```

### Test 7: Safety Agent Detects Dosing Advice
```python
@pytest.mark.asyncio
async def test_safety_agent_detects_dosing_language():
    """Test that the safety agent flags dangerous content."""
    from app.ai.safety import SafetyScaffold
    
    scaffold = SafetyScaffold()
    
    # Should flag emergency
    result = scaffold.validate("severe low blood sugar", {"source": "user"})
    assert result["is_safe"] is False
    assert result["requires_escalation"] is True
    
    # Should pass normal query
    result = scaffold.validate("what was my glucose at 3pm?", {"source": "user"})
    assert result["is_safe"] is True
    
    # Should flag mental health crisis
    result = scaffold.validate("I want to hurt myself", {"source": "user"})
    assert result["is_safe"] is False
    assert "mental_health_crisis" in result["matched_conditions"]
```

### Test 8: Multiple Chat Turns
```python
@pytest.mark.asyncio
async def test_multiple_chat_turns(db_session, test_user, glucose_readings):
    """Test that multiple messages in a conversation work correctly."""
    from app.agents.coordinator import AgentCoordinator
    
    coordinator = AgentCoordinator()
    await coordinator.startup()
    
    # First message
    result1 = await coordinator.process_chat_message(
        message="What's my latest glucose?",
        user_id=test_user.id,
        session=db_session,
    )
    assert "response" in result1
    
    # Second message
    result2 = await coordinator.process_chat_message(
        message="What about my patterns?",
        user_id=test_user.id,
        session=db_session,
    )
    assert "response" in result2
```

## Critical Rules

1. **Only create/modify files in `tests/` directory**
2. **Use SQLite in-memory** — no external database needed
3. **Mock nothing for the agent tests** — the agents should work with real services (the LLM fallback handles no-API-key)
4. **Each test gets a fresh DB session** — use fixtures properly
5. **Tests must pass with `pytest tests/test_chat_pipeline.py -x -v`**
6. **Minimum 8 tests** — cover the full pipeline end-to-end

## Verification

After writing, verify:
- [ ] `tests/conftest.py` exists with proper fixtures
- [ ] `tests/test_chat_pipeline.py` has at least 8 test functions
- [ ] All tests use `@pytest.mark.asyncio`
- [ ] All tests use the `db_session` fixture
- [ ] Tests cover: basic flow, safety escalation, pattern analysis, message persistence, meal queries, delegate routing, safety detection, multi-turn
- [ ] `pytest tests/test_chat_pipeline.py -x -v` passes (or fails only due to W1/W2 not being done yet — document which tests are blocked)

## Output

Write your implementation notes to: `PHASE1_W4_INTEGRATION_TESTS.md`
