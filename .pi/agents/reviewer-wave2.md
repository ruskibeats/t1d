---
name: reviewer-wave2
description: Reviews code changes from Wave 2 workers (W2 chat+RAG, W3 LLM fallback, W4 integration tests). Checks correctness, verifies the chat pipeline works end-to-end, and identifies issues. Part of the superteam review crew.
model: deepseek/deepseek-v4-flash
context: fork
---

# Reviewer — Wave 2

## Task

Review all code changes from Wave 2 workers and produce a comprehensive review report. Focus on the chat pipeline integration — W2 and W3 both touch `llm_service.py`, so conflicts are likely.

## Workers to Review

| Worker | Output File | Files Modified |
|--------|-------------|----------------|
| W2 | `PHASE1_W2_CHAT_RAG.md` | `app/api/chat.py`, `app/services/llm_service.py` |
| W3 | `PHASE1_W3_LLM_FALLBACK.md` | `app/services/llm_service.py` |
| W4 | `PHASE1_W4_INTEGRATION_TESTS.md` | `tests/test_chat_pipeline.py`, `tests/conftest.py` |

## Review Process

### Step 1: Read All Worker Output Files
Read each `PHASE*_W*.md` file.

### Step 2: Read All Modified Source Files
Read every modified file. Pay special attention to:
- `llm_service.py` — modified by BOTH W2 and W3. Check for conflicts.
- `chat.py` — the main chat endpoint. Verify it calls the coordinator correctly.
- `test_chat_pipeline.py` — verify tests actually test the real pipeline.

### Step 3: Check W2/W3 Conflict on `llm_service.py`
This is the highest-risk file. Both W2 and W3 modified it. Check:
- Did W3's fallback logic get placed correctly relative to W2's RAG changes?
- Is the `generate_response()` method correctly structured: try LLM → catch → fallback?
- Are there duplicate imports or conflicting changes?
- Does `_build_system_prompt()` receive and render pattern data correctly?

### Step 4: Verify the Chat Pipeline End-to-End
Trace the full flow:
1. `POST /api/v1/chat` → `chat()` endpoint
2. `chat()` → `coordinator.process_chat_message()` (from W1)
3. `coordinator` → `SafetyAgent` → `DataIngestionAgent` → `PatternAgent` → `ConversationAgent`
4. `ConversationAgent` → `LLMService.generate_response()`
5. `generate_response()` → `_call_llm()` → on failure → `_rule_based_response()`

Check that data flows correctly through each step.

### Step 5: Run Import Checks
```bash
python -c "from app.api.chat import router; print('chat OK')"
python -c "from app.services.llm_service import LLMService; print('llm OK')"
python -c "from app.agents.coordinator import AgentCoordinator; print('coordinator OK')"
```

### Step 6: Run Tests
```bash
pytest tests/ -x -v --timeout=120
```

## Output

Write your review to `REVIEW_WAVE2.md` using the same format as `REVIEW_WAVE1.md`.

## Critical Rules

1. **The W2/W3 conflict on `llm_service.py` is your #1 priority** — this is where things will break
2. **Verify the coordinator is actually called from the chat endpoint** — not just imported
3. **Check that the fallback chain works** — if LLM fails, does the rule-based response kick in?
4. **Run ALL tests** — the full test suite should pass after Wave 2

## Output

Write your review to: `REVIEW_WAVE2.md`
