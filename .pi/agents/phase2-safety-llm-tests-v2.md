---
name: phase2-safety-llm-tests-v2
description: Writes safety and LLM service tests. Use write() tool for ALL files. Do NOT output code in response text.
model: qwen/qwen3-coder-next
context: fork
---

# Phase 2: Safety + LLM Service Tests (v2)

## Task
1. Expand `tests/ai/test_safety.py` with new tests
2. Create `tests/test_llm_service.py` with mocked LLM tests

## CRITICAL RULES
1. Use the `write()` tool to create/overwrite files. NEVER output code in response text.
2. First read existing files to understand current code and test patterns.
3. Write each file in ONE write() call.

## Steps
1. Read existing files:
   - `tests/ai/test_safety.py` (already has ~15 tests)
   - `app/ai/safety.py`
   - `app/services/llm_service.py`

2. Use write() to overwrite `tests/ai/test_safety.py` — keep existing tests, ADD:
   - `test_policy_violation_dosing_advice()` — "take 5 units of insulin" → flagged
   - `test_policy_violation_treatment_change()` — "stop taking your insulin" → flagged
   - `test_policy_violation_missing_disclaimer()` — long response without "educational" → warning
   - `test_no_false_positive_on_educational_content()` — educational content → is_safe=True
   - `test_assistant_source_with_emergency_keywords()` — "kill yourself" in assistant output → is_safe=False
   - `test_assistant_source_safe_response()` — normal assistant response → is_safe=True
   - `test_severity_critical_for_diabetes_emergency()` — "severe low blood sugar" → critical
   - `test_severity_warning_for_general_medical()` — "I need help" → warning
   - `test_severity_safe_for_normal_query()` — "glucose at noon" → safe
   - `test_guardrails_all_severities()` — all conditions × severities produce guardrails
   - `test_guardrails_invalid_condition()` — unknown condition → empty list
   - `test_validate_whitespace_only()` — whitespace → is_safe=True
   - `test_validate_very_long_content()` — long normal text → is_safe=True
   - `test_validate_mixed_case_keywords()` — "SEVERE LOW BLOOD SUGAR" → is_safe=False
   - `test_validate_multiple_conditions()` — multiple categories matched

3. Use write() to create `tests/test_llm_service.py`:
   - MockTransport class for httpx
   - Fixtures: llm_service, mock_openrouter_response, mock_openai_response, mock_anthropic_response
   - Tests: retrieve_context_structure, retrieve_context_user_profile, retrieve_context_empty_data, retrieve_context_with_glucose, retrieve_context_with_events, build_system_prompt_includes_profile, build_system_prompt_includes_patterns, build_system_prompt_includes_events, build_conversation_history, build_conversation_history_max_turns, provider_enum_values, default_model_per_provider
   - Use `unittest.mock.patch` to mock httpx.AsyncClient for LLM API tests
   - All tests use @pytest.mark.asyncio

4. Run: `cd /root/t1d && python -m pytest tests/ai/test_safety.py -x -v --timeout=60`
5. Run: `cd /root/t1d && python -m pytest tests/test_llm_service.py -x -v --timeout=60`
6. Fix any failures and re-run until tests pass
7. Use write() to save notes to `PHASE2_W6_SAFETY_LLM_TESTS.md`

## Output
Write implementation notes to: `PHASE2_W6_SAFETY_LLM_TESTS.md`
