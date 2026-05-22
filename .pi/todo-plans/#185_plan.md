# Clanker Ops #185: E10-F1 Add simulator meal forecast scenario suite for validation

Status: pending
Tags: #meal-forecast #simulator #testing #scenarios #e10

## Intended Outcome
Extend the simulator validation lane so meal forecasting can be tested across controlled scenarios and cohorts before broader release.

## Scope
- Scenario fixtures
- Simulator-integrated forecast validation
- Cohort-level reports

## Implementation Steps
1. Define scenario set: high-carb breakfast, low-carb breakfast, mixed lunch, high-fat dinner, snack before exercise, low baseline + meal, high baseline + meal
2. Add scenario generator compatible with current simulator users
3. Produce expected forecast characteristics for each scenario
4. Run forecast engine against scenario meal/context pairs
5. Compare forecast results to simulated post-meal traces
6. Store evaluation outputs by run/scenario/user
7. Add regression tests for scenario outputs and tolerance thresholds

## Acceptance Criteria
- At least one scenario suite runs end-to-end in simulator mode
- Forecast timing and risk can be evaluated against simulated outcomes
- Regressions in forecast logic are caught automatically

## Dependencies
#184 - outcome evaluator must exist

## Done When
- Meal forecast has a repeatable simulator QA harness.