---
name: phase1-agent-coordinator
description: Wires up the T1D Companion agent coordinator by replacing stub implementations with real service delegation. Works on app/agents/coordinator.py. Use when implementing Phase 1 agent coordination.
model: openrouter/owl-alpha
context: fork
---

# Phase 1: Agent Coordinator Wiring

## Task

Replace ALL stub agent implementations in `app/agents/coordinator.py` with real delegation to the service layer. Every agent's `handle()` method must call actual services instead of returning placeholder data.

## Files to Modify

- `app/agents/coordinator.py` — the ONLY file you touch

## Current State (Stubs to Replace)

All 5 agents return placeholder data:
- `DataIngestionAgent.handle()` → returns `{"glucose": {"recent_count": 0, ...}, "events": [], "patterns": []}`
- `PatternAgent.handle()` → returns `{"patterns": [], "trends": {}, "correlations": []}`
- `ConversationAgent.handle()` → returns hardcoded string response
- `SummaryAgent.handle()` → returns `"Summary generation would happen here"`
- `SafetyAgent.handle()` → ALREADY WORKS (delegates to SafetyScaffold). Do NOT modify.

## Required Implementation

### DataIngestionAgent
```python
async def handle(self, data: dict) -> dict:
    action = data.get("action")
    if action == "get_context":
        from app.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        user_id = data["user_id"]
        # Use llm_service.retrieve_context(session, user_id) 
        # BUT we don't have a DB session here — return structure that 
        # ConversationAgent will fill in. Return the action spec.
        return {
            "action": "get_context",
            "user_id": user_id,
            "conversation_id": data.get("conversation_id"),
            "requires_session": True,
        }
    return {"status": "ok", "action": action}
```

Actually — better approach. The `AgentCoordinator.process_chat_message()` is the orchestrator. It has access to a DB session. The agents should accept the session as part of their `data` dict. Read `app/api/chat.py` to see how the coordinator is called.

### PatternAgent
```python
async def handle(self, data: dict) -> dict:
    action = data.get("action")
    if action == "analyze_for_conversation":
        from app.services.pattern_service import PatternService
        from datetime import datetime, timedelta, timezone
        from app.db.models import GlucoseReading, ContextEvent
        from sqlalchemy import select
        
        pattern_service = PatternService()
        user_id = data["user_id"]
        context = data.get("context", {})
        session = data.get("session")  # DB session passed from coordinator
        
        if not session:
            return {"patterns": [], "trends": {}, "correlations": [], "error": "no session"}
        
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
        
        return {
            "patterns": {
                "time_in_range": tir,
                "post_meal_spikes": {"count": len(spikes), "spikes": spikes[:3]},
                "overnight_hypoglycemia": {"count": len(overnight), "events": overnight[:3]},
            },
            "tir_percentage": tir.get("time_in_range", {}).get("percentage", 0),
            "estimated_a1c": tir.get("estimated_a1c", 0),
            "spike_count": len(spikes),
            "overnight_low_count": len(overnight),
        }
    
    return {"status": "ok", "action": action}
```

### ConversationAgent
```python
async def handle(self, data: dict) -> dict:
    message = data.get("message", "")
    user_id = data.get("user_id")
    session = data.get("session")
    context = data.get("context", {})
    patterns = data.get("patterns", {})
    
    if not session:
        return {
            "response": "I need a database session to generate a response.",
            "confidence": 0,
            "sources": [],
        }
    
    from app.services.llm_service import get_llm_service
    llm_service = get_llm_service()
    
    try:
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
```

### SummaryAgent
```python
async def handle(self, data: dict) -> dict:
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
    
    from app.services.llm_service import get_llm_service
    llm_service = get_llm_service()
    
    try:
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
```

### AgentCoordinator.process_chat_message()
Update to pass `session` through to all agents:
```python
async def process_chat_message(
    self,
    message: str,
    user_id: int,
    session,  # ADD THIS PARAMETER
    conversation_id: int | None = None,
) -> dict:
    # Safety check
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
    
    # Get context — pass session
    context = await self.agents["data_ingestion"].handle({
        "action": "get_context",
        "user_id": user_id,
        "conversation_id": conversation_id,
        "session": session,
    })
    
    # Analyze patterns — pass session
    pattern_result = await self.agents["pattern"].handle({
        "action": "analyze_for_conversation",
        "user_id": user_id,
        "context": context,
        "message": message,
        "session": session,
    })
    
    # Generate response — pass session
    response = await self.agents["conversation"].handle({
        "message": message,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "context": context,
        "patterns": pattern_result,
        "safety_result": safety_result,
        "session": session,
    })
    
    response["metadata"] = {
        "safety_checked": True,
        "patterns_analyzed": True,
        "context_included": bool(context),
    }
    
    return response
```

## Critical Rules

1. **Only modify `app/agents/coordinator.py`** — do NOT touch any other files
2. **Preserve the existing class structure** — BaseAgent, AgentCoordinator class signatures
3. **Preserve the `delegate_task()` method** — don't break existing callers
4. **Add `session` parameter to `process_chat_message()`** — this is the key change
5. **Import services inside methods** — avoid circular imports
6. **Handle errors gracefully** — if LLM fails, return a fallback response, don't crash
7. **Keep SafetyAgent unchanged** — it already works

## Verification

After writing, verify:
- [ ] All 5 agents have real implementations (SafetyAgent unchanged)
- [ ] `process_chat_message()` accepts a `session` parameter
- [ ] Session is passed through to DataIngestionAgent, PatternAgent, ConversationAgent
- [ ] PatternAgent calls `PatternService` methods with correct signatures
- [ ] ConversationAgent calls `LLMService.generate_response()` with correct signature
- [ ] SummaryAgent has both LLM and fallback summary generation
- [ ] No circular imports
- [ ] File passes `python -c "from app.agents.coordinator import AgentCoordinator; print('OK')"`

## Output

Write your implementation notes to: `PHASE1_W1_AGENT_COORDINATOR.md`
