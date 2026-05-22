---
name: "t1d-food-data-processing-modules"
description: "Build food data processing modules with confidence tracking. Use for creating nutrient extractors, serving normalizers, provenance models, and meal composition services. Pattern: dataclass models + deterministic functions + quality-based confidence scoring."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
display_name: "t1d:food-data-processing-modules"
---
## When to Use
Building food data processing modules for meal forecasting systems that need:
- Nutrient extraction from product databases
- Serving quantity normalization
- Data provenance/confidence tracking
- Meal composition aggregation
- Meal classification tags

## Procedure

1. **Define structured models with dataclasses**
   - Use `@dataclass` for input/output containers
   - Include confidence fields for quality tracking
   - Example: `NutrientProfile`, `NormalizedQuantity`, `FoodProvenance`

2. **Create deterministic extraction functions**
   - Accept product dict + quantity parameters
   - Return normalized values with confidence scores
   - Handle missing data gracefully (None → default values)

3. **Implement confidence scoring**
   - Base score on data completeness
   - Apply penalties for missing fields (barcode, serving weight, etc.)
   - Use QualityFlag enum for explicit issue tracking

4. **Write tests with realistic product structures**
   - Mock `OpenFoodFactsProduct` objects with typical fields
   - Test edge cases: missing serving weight, different units (g, ml, pieces)
   - Verify confidence calculations match expected penalties

5. **Compose higher-level services**
   - MealCompositionService aggregates multiple foods
   - PersonalContextService reads historical metrics
   - MealTags classifies based on nutrient thresholds

## Pitfalls
- Don't use dynamic field access (product['serving_quantity']) without None checks
- Serving normalization must handle 'piece' units specially (use product's serving_quantity)
- Confidence penalties should be proportional (0.05-0.1 per quality issue)

## Verification
- All tests pass with `pytest tests/test_*.py`
- Confidence scores match expected calculations
- Edge cases (None serving_weight, missing fields) handled gracefully