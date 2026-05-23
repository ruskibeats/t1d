# Clanker Ops #213: Fix cumulative drift across all anchors

## Intended Outcome
Meals return to baseline within 2-4 hours so glucose doesn't ratchet up across the day. Currently breakfast baseline=118, lunch baseline=154, dinner baseline=163. Target: all baselines within ~15 mg/dL of the overnight mean.

## Root Cause
Each meal is under-bolused by ~10% (intentional Tier 1 realism), but without any basal insulin to counteract the accumulating excess, the net effect is additive. Over 3 meals + occasional snacks, this adds ~50 mg/dL to the baseline by dinner.

## Options to Fix
1. **Add small pre-meal basal doses**: 0.3-0.5u rapid insulin 30 min before each meal. This resets the baseline without affecting meal rise visibility.
2. **Increase drift rate further**: Currently 0.020. At 0.030, half-life drops from ~6h to ~4h. Stronger pull toward baseline between meals.
3. **Tiered bolus**: First 60% of bolus at meal time (for spike control), remaining 40% delayed 60 min (for baseline recovery). Mirrors dual-wave bolus in real pumps.
4. **Symmetrical under-bolus**: Alternate meals — breakfast under-boluses, lunch fully boluses, dinner under-boluses. Net zero.

## Recommended Approach
Option 1 + 2 combined: add small basal doses 30 min before each meal (0.3-0.5u) and increase drift to 0.025. This is the most physiologically realistic and keeps the code simple.

## Files to modify
- `app/simulator/day_context.py` — add pre-meal basal doses in `_generate_insulin`
- `app/simulator/glucose_engine.py` — increase DRIFT_RATE from 0.020 to 0.025

## Verification
Run the calibration test for all 4 priority anchors. Expected:
- well_controlled: baselines should not drift more than 15 mg/dL across the day
- post_meal_spike: lunch can still drift, but breakfast baseline should be ~120
- overnight_hypo: dinner baseline should not rise
- brittle: baseline drift should be reduced

## Acceptance Criteria
- [ ] well_controlled breakfast→lunch→dinner baselines within 15 mg/dL
- [ ] Post_meal spike for lunch still reaches 200-240 range
- [ ] No new ceiling hits (0% for well_controlled)
- [ ] All 180+ tests pass