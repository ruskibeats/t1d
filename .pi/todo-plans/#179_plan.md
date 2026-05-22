# Clanker Ops #179: E4-F2 Add hour-of-day glucose baseline and variability features

Status: pending
Tags: #meal-forecast #hour-of-day #baseline #features #e4

## Objective
Formalize hour-of-day baseline and variability metrics as reusable personal-context features. The prototype already demonstrates this pattern informally; this task turns it into production logic. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)

## Scope
- Historical baseline by hour
- Variability features
- Stability/risk context helpers

## Implementation steps
1. Add query/service for hour-of-day aggregates from `health_metrics`.
2. Compute:
   - mean
   - median if useful
   - min/max
   - variability/standard deviation
   - sample count
   - recentness
3. Add feature outputs:
   - hour baseline band
   - stability level
   - morning sensitivity flag
   - recent volatility indicator
4. Define minimum data thresholds before feature is trusted.
5. Add tests with sparse and dense history fixtures.

## Acceptance criteria
- Hour-of-day features are reusable across forecast requests.
- Sparse data degrades confidence cleanly.
- Features are not mixed directly with narrative text.

## Verification
- Query simulated and real-like fixtures and confirm correct bands.
- Test with sparse and dense data scenarios.
- Verify minimum threshold behavior.

## Files/modules likely touched
- `app/services/baseline_features.py` (new)
- `tests/test_baseline_features.py`
- `app/db/models.py`

## Dependencies
#178 - personal context service must exist

## Done when
- Time-of-day context is a stable feature source for forecasts.