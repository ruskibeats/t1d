---
name: fixer-wave1
description: Reads the Wave 1 review report and applies fixes to the identified issues. Works on all files modified by Wave 1 workers. Part of the superteam fixer crew.
model: stepfun/step-3.5-flash
context: fork
---

# Fixer — Wave 1

## Task

Read `REVIEW_WAVE1.md` (written by the Wave 1 reviewer) and apply all fixes listed in the "Issues Requiring Fixes" table.

## Process

### Step 1: Read the Review Report
Read `REVIEW_WAVE1.md` completely. Understand every issue listed.

### Step 2: Prioritize Fixes
Fix in this order:
1. **High severity** — correctness bugs, import errors, security issues
2. **Medium severity** — missing edge cases, incomplete implementations
3. **Low severity** — style improvements, minor improvements

### Step 3: Apply Fixes
For each issue:
1. Read the file that needs fixing
2. Understand the existing code
3. Apply the minimal fix that resolves the issue
4. Verify the fix doesn't break anything else

### Step 4: Verify
After applying all fixes:
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

Then run tests:
```bash
pytest tests/ai/test_safety.py -x --timeout=60
pytest tests/test_pattern_service.py -x --timeout=60
pytest tests/test_llm_service.py -x --timeout=60
```

## Critical Rules

1. **Only fix what the review report says** — don't add new features or refactor unrelated code
2. **Minimal changes** — fix the issue, don't rewrite the surrounding code
3. **Preserve existing structure** — don't change function signatures or class hierarchies unless the review explicitly says to
4. **If a fix is unclear**, read the relevant worker's agent spec (`.pi/agents/phase*.md`) to understand the intent
5. **Don't modify test files** unless the review specifically identifies test issues
6. **If you can't fix an issue**, document why in the output

## Output

Write your fix report to `FIXES_WAVE1.md`:

```markdown
# Wave 1 Fix Report

## Fixes Applied
| # | File | Issue | Fix Applied | Status |
|---|------|-------|-------------|--------|
| 1 | file.py | description | what you did | ✅ Fixed |
| 2 | file.py | description | what you did | ✅ Fixed |
| 3 | file.py | description | couldn't fix because... | ❌ Blocked |

## Import Check Results
- coordinator.py: ✅ / ❌
- auth.py: ✅ / ❌
- ...

## Test Results
- test_safety.py: X passed, Y failed
- test_pattern_service.py: X passed, Y failed
- test_llm_service.py: X passed, Y failed

## Summary
- Total issues: N
- Fixed: N
- Blocked: N
- Ready for next wave: YES / NO
```
