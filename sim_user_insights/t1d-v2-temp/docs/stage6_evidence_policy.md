# Stage 6 Evidence Policy

How historical matches are treated when food matching confidence is weak.

## Evidence Tiers

| Confidence | Action |
|------------|--------|
| High (0.8-1.0) | Show similarity score, include in forecast bundle |
| Medium (0.5-0.8) | Show with caveat: "similar meals suggest..." |
| Low (0.2-0.5) | Suppress unless explicitly requested |
| None (<0.2) | Filter out, no historical context |

## Suppression Rules

Historical matches are filtered when:
1. Any food in meal has `confidence < 0.5`
2. Fast-carb match is absent for high-sugar meal (>25% sugars)
3. Fat/protein matching is high-uncertainty and meal is high-fat (>15g fat)

## Annotation Rules

When included, annotate with:
- `similar_meals` count and avg peak delta
- `confidence_tier` in narrative ("some / strong / limited evidence")
- `narrative` explains what was actually matched

## Downgrade Triggers

If `evidence_items` contains:
- Any `confidence: "low"` → downgrade whole forecast to "medium" overall
- Missing macros (fat, protein) → flag `incomplete_nutrition_data`
- Fast-food fallback → flag `using_known_values`

## Implementation

See: `companion_pipeline_v2.py` stage_historical_context() and `t1d_llm_context.py` check_safety()