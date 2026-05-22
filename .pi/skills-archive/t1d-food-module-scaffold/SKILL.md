---
name: "t1d-food-module-scaffold"
description: "Build food data processing modules with dataclass-based contracts and comprehensive tests"
version: 2
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use
When building new food-related modules (nutrient extraction, serving normalization, provenance, meal composition) in the T1D Companion project.

## Procedure
1. **Create the module file** in `app/food/` or `app/services/`:
   - Define dataclasses with `@dataclass` decorator for type safety
   - Use `from __future__ import annotations` for forward references
   - Keep functions pure and deterministic
   - Add docstrings explaining the deterministic logic

2. **Write the test file** in `tests/`:
   - Import from the app module
   - Test edge cases: None values, missing fields, unit conversions
   - Use pytest fixtures for test data setup
   - Test confidence score boundaries (0.0-1.0 range)

3. **Run tests** with `python -m pytest tests/test_*.py -v`:
   - Fix any failures immediately
   - Verify all edge cases covered
   - Check for validation errors before marking complete

4. **Update the plan file** with completion notes

5. **Mark task complete** in todo system
## Key Patterns
- `NutrientProfile`: grams protein/carbs/fat, calories, sodium, confidence
- `NormalizedQuantity`: quantity_g, confidence, source_provenance
- `FoodProvenance`: source_name, trust_tier, quality_flags, confidence score
- `HourBaselineFeatures`: median, std_dev, stability, variability per hour

## Pitfalls to Avoid
- Don't create too many plan files - user wants implementation
- Don't use `old_text`/`new_text` in edit tool - use `oldText`/`newText`
- Don't use `file` parameter in write tool - use `path` and `content`

## Verification
- All tests pass: `pytest tests/test_<module>.py`
- Import checks: Python imports resolve correctly