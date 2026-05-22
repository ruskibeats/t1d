# Clanker Ops #188: T20 iOS proof of concept consuming structured MealForecastResponse

Status: pending
Tags: #meal-forecast #ios #poc #client #t20

## Intended Outcome
Build a thin iOS proof of concept that consumes the structured forecast response and renders the feature without depending on generated prose as its only source of truth.

## Scope
- Basic request/response integration
- Rendering of structured forecast
- Safe degraded states

## Implementation Steps
1. Create Swift models matching the response contract
2. Add API client method for POST /meal-forecast
3. Build simple screen showing: meal totals, risk tier, timing window, personal context note, confidence, safety note
4. Add "why this forecast?" expandable debug section for internal builds
5. Add low-confidence / unavailable UI states
6. Confirm the client does not reconstruct logic locally

## Acceptance Criteria
- iOS can render a real forecast end-to-end
- UI works from structured response fields even if narrative is absent
- Debug/internal builds can inspect evidence without exposing it in public UX

## Dependencies
#187 - feature flags and admin debug must exist

## Done When
- The client proves the API contract is practical and sufficient.