# Clanker Ops #183: E8-F1 Add POST /meal-forecast endpoint and meal_forecasts persistence

Status: pending
Tags: #meal-forecast #api #persistence #alembic #e8

## Intended Outcome
Expose the meal forecast capability as a stable API endpoint and persist all forecast inputs/outputs for replay, evaluation, and audit.

## Scope
- API route
- Forecast persistence tables
- Debug-safe storage of evidence

## Implementation Steps
1. Add Alembic migration for: meal_forecasts, meal_forecast_items, optional meal_forecast_feedback
2. Define ORM models
3. Add POST /meal-forecast endpoint
4. Wire request through: food normalization, meal composition, personal context, forecast engine, safety validator, narrative generator
5. Persist request snapshot, structured forecast, evidence, narrative, confidence, and safety flags
6. Return response using canonical Pydantic schema
7. Add tests for success, validation failure, and auth/flag behavior

## Acceptance Criteria
- Endpoint returns forecast successfully for valid payloads
- Forecasts are persisted and replayable
- Stored evidence supports later evaluation/debugging

## Dependencies
#182 - narrative generator must exist

## Done When
- Forecast is a first-class backend API, not an ad hoc computation.