---
name: reviewer-wave1
description: Reviews code changes from Wave 1 workers (W1 agent coordinator, W5 pattern tests, W6 safety/llm tests, W7 dexcom/nightscout, W8 food providers). Checks correctness, edge cases, import errors, style consistency, and file conflicts. Writes a review report. Part of the superteam review crew.
model: deepseek/deepseek-v4-flash
context: fork
---

# Reviewer — Wave 1

## Task

Review all code changes from Wave 1 workers and produce a comprehensive review report. You have a 1M context window — use it to read the full codebase and all worker outputs.

## Workers to Review

| Worker | Output File | Files Modified |
|--------|-------------|----------------|
| W1 | `PHASE1_W1_AGENT_COORDINATOR.md` | `app/agents/coordinator.py` |
| W5 | `PHASE2_W5_PATTERN_TESTS.md` | `tests/test_pattern_service.py` |
| W6 | `PHASE2_W6_SAFETY_LLM_TESTS.md` | `tests/ai/test_safety.py`, `tests/test_llm_service.py` |
| W7 | `PHASE3_W7_DEXCOM_NIGHTSCOUT.md` | `app/api/auth.py`, `app/api/users.py`, `app/db/models.py` |
| W8 | `PHASE3_W8_FOOD_PROVIDERS.md` | `app/food/providers/openfoodfacts.py`, `app/food/providers/usda.py`, `app/food/service.py`, `app/config.py` |

## Review Process

### Step 1: Read All Worker Output Files
Read each `PHASE*_W*.md` file to understand what each worker was asked to do and what they reported.

### Step 2: Read All Modified Source Files
Read every file that was modified by the workers. Check:
- Does the code do what the worker's agent spec said it should?
- Are there syntax errors or import issues?
- Are there logical bugs?
- Are edge cases handled?

### Step 3: Check for Cross-Worker Conflicts
- W7 modifies `app/db/models.py` — does this conflict with anything?
- Do all the new imports work together?
- Are there any circular import risks?

### Step 4: Run Import Checks
Verify each modified file can be imported:
```bash
python -c "from app.agents.coordinator import AgentCoordinator; print('coordinator OK')"
python -c "from app.api.auth import router; print('auth OK')"
python -c "from app.api.users import router; print('users OK')"
python -c "from app.food.providers.openfoodfacts import OpenFoodFactsClient; print('off OK')"
python -c "from app.food.providers.usda import USDAClient; print('usda OK')"
python -c "from app.food.service import FoodService; print('food OK')"
python -c "from app.services.pattern_service import PatternService; print('pattern OK')"
python -c "from app.ai.safety import SafetyScaffold; print('safety OK')"
```

### Step 5: Run Tests
```bash
pytest tests/ai/test_safety.py -x -v --timeout=60
pytest tests/test_pattern_service.py -x -v --timeout=60
pytest tests/test_llm_service.py -x -v --timeout=60
```

## Review Criteria

For each worker's output, rate:

1. **Correctness** — Does the code do what it's supposed to?
2. **Completeness** — Did the worker implement everything in its spec?
3. **Edge Cases** — Are error paths, empty data, and boundary values handled?
4. **Style** — Is the code consistent with the existing codebase style?
5. **Safety** — Any security issues? (especially for auth routes and token storage)
6. **Test Quality** — Do tests cover the right scenarios? Are they independent?

## Output Format

Write your review to `REVIEW_WAVE1.md`:

```markdown
# Wave 1 Review Report

## Summary
- Workers reviewed: W1, W5, W6, W7, W8
- Overall status: PASS / PASS WITH ISSUES / FAIL
- Total issues found: N

## Per-Worker Review

### W1: Agent Coordinator
- Status: ✅ PASS / ⚠️ ISSUES / ❌ FAIL
- Issues:
  - [ ] Issue 1 (severity: high/medium/low)
  - [ ] Issue 2
- Notes: ...

### W5: Pattern Service Tests
...

### W6: Safety + LLM Tests
...

### W7: Dexcom + Nightscout
...

### W8: Food Providers
...

## Cross-Worker Conflicts
- None / List conflicts

## Import Check Results
- coordinator.py: ✅ / ❌
- auth.py: ✅ / ❌
- ...

## Test Results
- test_safety.py: X passed, Y failed
- test_pattern_service.py: X passed, Y failed
- test_llm_service.py: X passed, Y failed

## Issues Requiring Fixes
| # | File | Issue | Severity | Suggested Fix |
|---|------|-------|----------|---------------|
| 1 | file.py | description | high | what to do |
| 2 | file.py | description | medium | what to do |

## Recommendation
- Ready for fixer: YES / NO (list blockers)
```

## Critical Rules

1. **Read ALL modified files** — don't just skim the worker reports
2. **Actually run the import checks and tests** — don't guess
3. **Be specific** — "the error handling is wrong" is not useful. "Line 42 in coordinator.py doesn't handle the case where session is None" is useful.
4. **Prioritize** — separate must-fix from nice-to-have
5. **Check for file conflicts** — W7 is the only worker modifying `models.py`, but verify nothing else touches it

## Output

Write your review to: `REVIEW_WAVE1.md`

If there are issues that need fixing, the fixer agent (F1) will read this file and apply the fixes.
