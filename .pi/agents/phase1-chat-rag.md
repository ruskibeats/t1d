---
name: phase1-chat-rag
description: Fixes the T1D Companion chat endpoint and RAG pipeline. Removes keyword-matching fake AI, wires chat to AgentCoordinator, and enriches RAG context with pattern summaries. Use when implementing Phase 1 chat pipeline.
model: nvidia/nemotron-3-super-120b-a12b:free
context: fork
---

# Phase 1: Chat Endpoint + RAG Pipeline Fix

## Task

Two tightly coupled fixes:
1. **Fix `app/api/chat.py`** — remove the fake keyword-matching `_generate_ai_response()`, wire the chat endpoint to call `AgentCoordinator.process_chat_message()` 
2. **Fix `app/services/llm_service.py`** — enrich `retrieve_context()` to include pattern summaries (TIR, spikes, overnight lows) so the LLM gets grounded data

## Files to Modify

- `app/api/chat.py` — remove fake AI, wire to real pipeline
- `app/services/llm_service.py` — enrich RAG context

## Part 1: Fix `app/api/chat.py`

### What to Remove
Delete the entire `_generate_ai_response()` function — it's the big if/else keyword tree that returns hardcoded responses based on `"spike" in message_lower` etc.

### What to Change in `chat()` endpoint

The endpoint already:
- Gets/creates a conversation
- Saves the user message to DB
- Calls `_build_context()` for glucose + events
- Calls `_generate_ai_response()` ← REPLACE THIS
- Saves the AI response to DB

Replace the `_generate_ai_response()` call with:

```python
from app.agents.coordinator import AgentCoordinator

# Get the global coordinator (from app.main)
from app.main import app as fastapi_app
coordinator = getattr(fastapi_app.state, 'coordinator', None)

if coordinator:
    try:
        ai_response = await coordinator.process_chat_message(
            message=request.message,
            user_id=user.id,
            session=session,
            conversation_id=conversation.id,
        )
        
        if "error" in ai_response:
            ai_response_text = ai_response.get("message", "An error occurred.")
        else:
            ai_response_text = ai_response.get("response", "")
    except Exception as e:
        logger.error(f"Agent coordinator failed: {e}")
        ai_response_text = (
            "I'm having trouble processing your request right now. "
            "Please try again in a moment."
        )
else:
    ai_response_text = (
        "The AI assistant is not available right now. "
        "Please try again later."
    )
```

### What to Change in `chat_stream()` endpoint

Same replacement — instead of:
```python
response_text = _generate_ai_response(request.message, context, user)
```

Use the coordinator call. For streaming, you can either:
- Block and stream word-by-word (simpler, matches current pattern)
- Or use the LLM service's native streaming (better, more complex)

For now, block on the coordinator call, then stream the response word-by-word (the existing SSE loop is fine).

### Enhance `_build_context()` to include patterns

Add pattern analysis to the context builder:

```python
# After fetching events, add pattern analysis:
from app.services.pattern_service import PatternService
from datetime import datetime, timedelta, timezone

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
    }
except Exception as e:
    logger.warning(f"Pattern analysis failed in chat context: {e}")
    context["pattern_summary"] = None
```

## Part 2: Fix `app/services/llm_service.py`

### Fix `retrieve_context()`

Currently fetches glucose readings and events but NO pattern analysis. Add:

```python
# After fetching events (around line 120), add pattern analysis:
from app.services.pattern_service import PatternService as PatternSvc

pattern_svc = PatternSvc()
end_date = datetime.now(timezone.utc)
start_date = end_date - timedelta(days=time_range_days)

try:
    tir = await pattern_svc.calculate_time_in_range(
        session, user_id, start_date, end_date
    )
    spikes = await pattern_svc.detect_post_meal_spikes(
        session, user_id, start_date, end_date
    )
    overnight = await pattern_svc.detect_overnight_hypoglycemia(
        session, user_id, start_date, end_date
    )
    
    pattern_summary = {
        "time_in_range_percentage": tir.get("time_in_range", {}).get("percentage", 0),
        "time_below_range_percentage": tir.get("time_in_range", {}).get("below_range", {}).get("percentage", 0),
        "time_above_range_percentage": tir.get("time_in_range", {}).get("above_range", {}).get("percentage", 0),
        "estimated_a1c": tir.get("estimated_a1c", 0),
        "average_glucose": tir.get("readings", {}).get("average", 0),
        "post_meal_spike_count": len(spikes),
        "overnight_low_count": len(overnight),
        "grade": tir.get("grade", "N/A"),
    }
except Exception as e:
    self.logger.warning(f"Pattern analysis failed in RAG: {e}")
    pattern_summary = None
```

Then include `pattern_summary` in the returned `RAGContext`.

### Fix `_build_system_prompt()`

The method already has a section for pattern summary:
```python
if rag_context.pattern_summary:
    tir = rag_context.pattern_summary.get("time_in_range", {})
    prompt += f"""
Recent Pattern Summary (last 14 days):
- Time in range: {tir.get('percentage', 0):.1f}% (target 70-180 mg/dL)
...
```

But `RAGContext.pattern_summary` is currently always `None` because `retrieve_context()` never sets it. Your fix to `retrieve_context()` will make this work.

Verify the `RAGContext` model has a `pattern_summary` field. If not, add it:
```python
class RAGContext(BaseModel):
    recent_glucose: List[Dict[str, Any]] = Field(default_factory=list)
    recent_events: List[Dict[str, Any]] = Field(default_factory=list)
    pattern_summary: Optional[Dict[str, Any]] = Field(None)
    user_profile: Optional[Dict[str, Any]] = Field(None)
```

## Critical Rules

1. **Only modify `app/api/chat.py` and `app/services/llm_service.py`**
2. **Preserve all existing endpoint signatures** — don't break the API contract
3. **Preserve message persistence** — user and AI messages must still be saved to DB
4. **Handle coordinator unavailability gracefully** — if coordinator is None, return a friendly error
5. **Handle pattern analysis failures gracefully** — wrap in try/except, set to None on failure
6. **Don't change the streaming SSE format** — keep the same `StreamingChunk` structure
7. **Remove `_generate_ai_response()` entirely** — it's dead code after this change

## Verification

After writing, verify:
- [ ] `_generate_ai_response()` is completely removed from `chat.py`
- [ ] `chat()` endpoint calls `coordinator.process_chat_message()` with session
- [ ] `chat_stream()` endpoint uses the same pipeline
- [ ] `_build_context()` includes pattern analysis
- [ ] `retrieve_context()` in `llm_service.py` includes pattern summaries
- [ ] `RAGContext` model has `pattern_summary` field
- [ ] `_build_system_prompt()` renders pattern data
- [ ] No import errors: `python -c "from app.api.chat import router; print('OK')"`
- [ ] No import errors: `python -c "from app.services.llm_service import LLMService; print('OK')"`

## Output

Write your implementation notes to: `PHASE1_W2_CHAT_RAG.md`
