# Clanker Ops #180: E5-F1 Build deterministic MealForecastEngine with structured evidence

Status: pending
Tags: #meal-forecast #engine #deterministic #evidence #e5

## Objective
Create the core deterministic engine that turns meal composition and personal context into structured forecast outputs. This engine must be fully testable, non-LLM, and evidence-first. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)

## Scope
- Risk determination
- Timing windows
- Confidence computation
- Evidence mapping

## Implementation steps
1. Define engine input object: meal profile + personal context + optional live context.
2. Define engine outputs:
   - risk level
   - timing onset window
   - peak window
   - delayed effect flag
   - confidence
   - evidence reasons
3. Encode deterministic rules for:
   - high carb load
   - morning sensitivity
   - elevated baseline
   - mixed/high-fat meals
   - limited confidence due to poor food quality or sparse history
4. Add explanation-ready evidence keys.
5. Add unit tests covering meal/user/time combinations.

## Acceptance criteria
- Engine produces the same output for the same input.
- Every conclusion is backed by evidence fields.
- No direct narrative logic or LLM dependency inside the engine.

## Verification
- Recreate the eggs + bread example from paste and inspect structured output. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)
- Test deterministic behavior across multiple runs.
- Verify evidence fields are populated correctly.

## Files/modules likely touched
- `app/services/meal_forecast_engine.py` (new)
- `tests/test_meal_forecast_engine.py`
- `app/models/meal_forecast.py`

## Dependencies
#179 - hour-of-day baseline features must exist

## Done when
- Forecast reasoning is formalized and testable.