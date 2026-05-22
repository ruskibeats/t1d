# Clanker Ops #187: E12-F1 Add feature flags and admin debug endpoint

Status: pending
Tags: #meal-forecast #feature-flags #admin #debug #e12

## Intended Outcome
Add safe rollout controls and an admin-only debug surface for meal forecasts so the feature can be enabled by cohort, inspected with full evidence, and disabled instantly if unsafe or unstable behavior is detected.

## Scope
- Feature flag for meal forecasting at global, cohort, and user level
- Admin-only debug endpoint returning full structured evidence for a forecast
- Kill switch support
- Audit logging for flag changes and debug access

## Implementation Steps
1. Add feature flag storage: existing config table/pattern or new feature_flags table plus optional user_feature_overrides
2. Define flags: meal_forecast_enabled, meal_forecast_debug_enabled, meal_forecast_simulator_only, meal_forecast_internal_beta
3. Add backend guard in forecast endpoint path before execution
4. Add admin-only GET /admin/meal-forecast/debug/{forecast_id} endpoint
5. Return raw evidence objects, confidence inputs, food provenance, personal context, safety validator results
6. Add audit log event for flag reads, flag changes, debug endpoint access
7. Add tests for denied access, allowed admin access, flag-based enable/disable behavior

## Acceptance Criteria
- Forecast endpoint can be disabled globally without deploy
- Debug endpoint is inaccessible to normal users
- Admin debug returns structured evidence, not just final narrative
- All accesses are auditable

## Dependencies
#186 - food quality flags must exist

## Done When
- Safe progressive rollout and emergency shutdown are possible from backend controls alone.