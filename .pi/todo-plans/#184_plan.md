# Clanker Ops #184: E9-F1 Build outcome evaluator comparing forecast vs post-meal glucose

Status: pending
Tags: #meal-forecast #evaluation #metrics #outcome #e9

## Intended Outcome
Create an evaluator that measures whether forecasted timing, rise risk, and confidence match observed post-meal glucose behavior.

## Scope
- Post-meal evaluation windows
- Timing/risk comparison logic
- Metrics and reporting

## Implementation Steps
1. Define evaluation windows: 0–60, 60–120, 120–240 minutes after meal
2. Define observed outcome metrics: rise detected yes/no, time to initial rise, time to peak, peak magnitude band, delayed rise present/absent
3. Build evaluator service that takes stored forecast + observed glucose trace
4. Compare forecasted risk/timing against observed outcomes
5. Compute summary metrics: calibration by risk tier, timing accuracy, false reassurance rate, over-warning rate
6. Persist evaluation results
7. Add SQL/report outputs for cohort review

## Acceptance Criteria
- Every stored forecast can be evaluated later
- Metrics are available per user, meal class, and cohort
- Unsafe miss categories are measurable

## Dependencies
#183 - meal forecast endpoint must exist

## Done When
- Forecast performance can be quantified over time.