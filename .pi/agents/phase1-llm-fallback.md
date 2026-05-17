---
name: phase1-llm-fallback
description: Adds a rule-based fallback response generator to the T1D Companion LLM service so the chat pipeline works end-to-end without any API key. Use when implementing Phase 1 LLM fallback.
model: poolside/laguna-m.1:free
context: fork
---

# Phase 1: LLM Fallback Chain

## Task

Add a rule-based fallback response generator to `app/services/llm_service.py` so the chat pipeline works end-to-end even when no LLM API key is configured. The fallback uses the RAG context (glucose readings, events, pattern summaries) to generate informative responses without calling any external API.

## Files to Modify

- `app/services/llm_service.py` — add fallback logic

## Current State

The `LLMService` tries to call OpenRouter/OpenAI/Anthropic. If no API key is configured, it raises `LLMServiceError("OpenRouter API key not configured")`. The chat pipeline crashes.

## Required Implementation

### Step 1: Add a `_rule_based_response()` method

Add this method to the `LLMService` class:

```python
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
    
    # Build response based on query type and available data
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
```

### Step 2: Modify `generate_response()` to use fallback

In the `generate_response()` method, wrap the LLM call in a try/except:

```python
# After building messages, try LLM first, then fallback:
try:
    if stream:
        response = await self._call_llm(messages, max_tokens, stream=False)
        return {**response, "streamed": False}
    else:
        response = await self._call_llm(messages, max_tokens, stream=False)
        return response
except (LLMServiceError, Exception) as e:
    self.logger.warning(f"LLM call failed, using fallback: {e}")
    return await self._rule_based_response(message, rag_context)
```

### Step 3: Make API key checks non-fatal

In `_get_openrouter_key()`, `_get_openai_key()`, `_get_anthropic_key()` — instead of raising `LLMServiceError` when no key is found, return `None` and let the fallback handle it:

```python
def _get_openrouter_key(self) -> str | None:
    """Get OpenRouter API key. Returns None if not configured."""
    import os
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        try:
            key = get_settings().openrouter_api_key
        except Exception:
            pass
    return key  # Can be None — fallback will handle it
```

Then in `_call_llm()`, check if the key is None and raise `LLMServiceError` with a clear message so the fallback kicks in:

```python
async def _call_llm(self, messages, max_tokens, stream):
    if self.provider == LLMProvider.OPENROUTER:
        key = self._get_openrouter_key()
        if not key:
            raise LLMServiceError("No OpenRouter API key configured")
        return await self._call_openrouter(messages, max_tokens, stream)
    # ... etc
```

## Critical Rules

1. **Only modify `app/services/llm_service.py`**
2. **Don't break existing LLM provider logic** — if a key is configured, use the real LLM
3. **Fallback must use RAG context** — the whole point is that responses are grounded in user data
4. **Never give dosing advice** — the fallback must follow the same safety rules as the LLM
5. **Keep responses concise** — 2-4 sentences per topic, not essays
6. **Always include a disclaimer** — remind users this is educational, not medical advice

## Verification

After writing, verify:
- [ ] `_rule_based_response()` method exists and handles all query types
- [ ] `generate_response()` catches LLM errors and falls back gracefully
- [ ] API key methods return None instead of raising when no key is configured
- [ ] Fallback responses include glucose data when available
- [ ] Fallback responses include pattern summaries when available
- [ ] No dosing advice in any fallback response
- [ ] No import errors: `python -c "from app.services.llm_service import LLMService; print('OK')"`

## Output

Write your implementation notes to: `PHASE1_W3_LLM_FALLBACK.md`
