# Clanker Ops #178: E4-F1 Build PersonalContextService using health_metrics history

Status: pending
Tags: #meal-forecast #personal-context #health-metrics #service #e4

## Objective
Build a service that computes the user-specific metabolic context needed for meal forecasting using recent glucose history and stored user parameters. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)

## Scope
- Recent baseline context
- Historical context assembly
- Simulator/real-user compatibility

## Implementation steps
1. Define `PersonalContext` output schema.
2. Pull recent glucose window from `health_metrics`.
3. Add optional parameter lookups from user profile and simulator profile paths.
4. Call hour-of-day baseline feature logic.
5. Add trend classification: rising, flat, falling, unknown.
6. Add missing-data handling and confidence downgrade behavior.
7. Add tests for:
   - recent data present
   - sparse history
   - simulator users
   - real users

## Acceptance criteria
- Service returns one normalized context object.
- Forecast engine can use the same context shape regardless of user type.
- Missing history does not crash the feature.

## Verification
- Run against a known sim user from the paste flow and inspect output. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)
- Test with sparse and dense history fixtures.
- Verify simulator compatibility.

## Files/modules likely touched
- `app/services/personal_context_service.py` (new)
- `tests/test_personal_context_service.py`
- `app/models/meal_forecast.py`
- `app/db/models.py` (health_metrics)

## Dependencies
#177 - meal tags must exist

## Done when
- Personal context is abstracted into a dedicated reusable service.