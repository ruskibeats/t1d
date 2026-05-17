---
name: phase2-pattern-tests-v2
description: Writes unit tests for PatternService. Use write() tool for ALL files. Do NOT output code in response text.
model: openai/gpt-oss-120b:free
context: fork
---

# Phase 2: Pattern Service Tests (v2)

## Task
Write `tests/test_pattern_service.py` with 37+ unit tests for `app/services/pattern_service.py`.

## CRITICAL RULES
1. Use the `write()` tool to create files. NEVER output code in your response text.
2. First read `app/services/pattern_service.py` to understand the actual method signatures.
3. First read `tests/ai/test_safety.py` to understand the existing test patterns.
4. First read `app/db/models.py` to understand the model fields.
5. Write the file in ONE write() call. Do not split into multiple writes.

## Steps
1. Read the source files listed above
2. Use write() to create `tests/test_pattern_service.py` with:
   - SQLite in-memory test setup (reuse pattern from existing tests)
   - Fixtures: db_session, test_user, glucose_dataset, meal_events, exercise_events
   - Tests for: calculate_time_in_range (12 tests), detect_post_meal_spikes (8 tests), detect_overnight_hypoglycemia (5 tests), analyze_exercise_impact (4 tests), detect_delayed_high_fat_effects (3 tests), analyze_correlations (3 tests), generate_statistical_summary (2 tests)
   - All tests use @pytest.mark.asyncio
3. Use write() to create `tests/conftest.py` if it doesn't exist with shared fixtures
4. Run: `cd /root/t1d && python -m pytest tests/test_pattern_service.py -x -v --timeout=120`
5. Fix any failures and re-run until tests pass
6. Use write() to save notes to `PHASE2_W5_PATTERN_TESTS.md`

## Output
Write implementation notes to: `PHASE2_W5_PATTERN_TESTS.md`
