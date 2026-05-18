# Todo #37: [GRAPH-5] Wire remaining pattern detections to graph edges

Status: pending
Owner: UNASSIGNED
Tags: graph, backend, p0

## Plan
1. Review `app/services/pattern_service.py` for existing meal→spike edge writing
2. Add delayed high-fat meal detection: link fat/calories → delayed glucose spike (edge type: `meal_to_delayed_spike`)
3. Add exercise impact detection: link exercise → glucose change (edge type: `exercise_to_glucose_drop` or `exercise_to_glucose_rise`)
4. Add overnight low detection: link sleep/heart metrics → low glucose (edge type: `heart_rate_to_low_glucose` or `sleep_to_next_day_glucose`)
5. Add insulin historical detection: link insulin → subsequent glucose change (edge type: `insulin_to_glucose_change`)
6. Add correlation analysis persistence (not just JSON response)
7. Make edge-writing optional/configurable to avoid duplicate writes
8. Add tests for each new edge type

## Verification
- Each pattern detection creates appropriate graph edges with evidence metadata
- Edge-writing can be toggled off for read-only analyses
- Tests pass for all new edge types

## Intercom Rules
- If blocked, use `intercom({ action: "reply", message: "BLOCKED: <reason>" })`
- Do NOT silently fail — always report back

## Discovered Work
- If pattern detection reveals data quality issues, report via intercom
