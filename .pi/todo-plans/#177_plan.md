# Clanker Ops #177: E3-F2 Add meal tags (low-carb, high-fat, etc) and carb-load classes

Status: pending
Tags: #meal-forecast #meal-tags #classification #e3

## Objective
Add deterministic meal classification tags that help the forecast engine and UI interpret a meal beyond raw totals. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)

## Scope
- Meal tags
- Carb-load class
- Threshold definitions

## Implementation steps
1. Define threshold-based tags:
   - low-carb
   - moderate-carb
   - high-carb
   - high-protein
   - high-fat
   - mixed meal
   - light snack
2. Encode thresholds in one config module.
3. Add tag generation to meal composition output.
4. Add tests covering edge thresholds and combined tags.

## Acceptance criteria
- Tags are deterministic and centrally defined.
- Forecast engine can consume tags without recalculating thresholds.
- UI can display tags directly if needed.

## Verification
- Test with eggs + bread and confirm expected classes. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)
- Verify edge cases at threshold boundaries.
- Confirm tag combinations work correctly.

## Files/modules likely touched
- `app/food/meal_tags.py` (new)
- `tests/test_meal_tags.py`
- `app/food/meal_composition_service.py`

## Dependencies
#176 - meal composition service must exist

## Done when
- Meal semantics are represented consistently across the stack.