# Phase 1, W3: LLM Fallback Implementation

## Status: ✅ COMPLETE

## Changes Made

### 1. Added `_rule_based_response()` Method

New method to `LLMService` class that generates responses from RAG context without calling any external API:

- **Glucose queries** — Returns recent reading value, trend, timestamp, and average over last 10 readings
- **Pattern/TIR queries** — Returns time in range %, estimated A1C, average glucose, spike count, overnight lows
- **Meal/food queries** — Returns logged meal count, recent meal carbs, post-meal spike observations
- **Insulin queries** — Returns insulin entry count, explicitly states "can't provide dosing recommendations"
- **Exercise queries** — Returns exercise session count, safety reminder about monitoring glucose
- **Help/general** — Lists available topics, reminds user this is educational not medical advice
- **Fallback** — Shows latest glucose and TIR for unrecognized queries

Returns dict with:
```python
{
    "response": str,
    "tokens_used": 0,
    "model": "rule-based-fallback",
    "provider": "fallback",
    "streamed": False,
    "safety_flagged": False,
}
```

### 2. Modified `generate_response()` Method

Wrapped LLM call in try/except block:
```python
try:
    response = await self._call_llm(messages, max_tokens, stream=False)
    return response
except (LLMServiceError, Exception) as e:
    self.logger.warning(f"LLM call failed, using fallback: {e}")
    return await self._rule_based_response(message, rag_context)
```

### 3. Modified API Key Methods

Changed `_get_openai_key()`, `_get_anthropic_key()`, `_get_openrouter_key()` to return `Optional[str]` instead of raising:
- Returns `None` when no key is configured
- `LLMServiceError` is raised in `_call_llm()` if key is `None`, triggering the fallback

## Verification

- ✅ `_rule_based_response()` method exists
- ✅ `generate_response()` catches LLM errors and falls back gracefully
- ✅ API key methods return `None` instead of raising when no key configured
- ✅ Fallback responses include glucose data when available
- ✅ Fallback responses include pattern summaries when available
- ✅ No dosing advice in any fallback response
- ✅ `python -c "from app.services.llm_service import LLMService; print('OK')"` passes

## File Modified

- `app/services/llm_service.py` — Added `_rule_based_response()`, modified `generate_response()`, modified key getter methods