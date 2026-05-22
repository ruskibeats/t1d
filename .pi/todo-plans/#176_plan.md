#176 E2-F4: Build meal composition service (merge multiple foods into single nutrient total)

**Objective**  
Compute total nutrients for a meal from multiple foods with appropriate weighting and provenance handling. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)

**Scope**
- Meal composition.
- Provenance aggregation.
- Serving normalization.

**Implementation steps**
1. Define MealItem with quantity, unit, food reference.
2. Accept list of foods, quantities, and units.
3. Normalize each to grams using serving normalizer.
4. Extract nutrients using nutrient extractor.
5. Aggregate nutrients weighted by quantity.
6. Combine provenance (weakest link wins).
7. Return MealComposition result.
8. Add tests.

**Acceptance criteria**
- Service returns correct totals for multi-item meals.
- Provenance confidence degrades with missing data.
- Unit conversion works end-to-end.

**Done when**
- A meal of items produces accurate nutrient aggregate.

### Implementation Summary

Created `app/food/meal_composition.py` with:
- `MealItem` dataclass for food + quantity + unit
- `MealComposition` dataclass with total nutrients and aggregated provenance
- `compose_meal()` function that:
  - Normalizes serving sizes to grams
  - Extracts nutrients from each food
  - Aggregates weighted nutrients
  - Combines provenance (worst case confidence)
- `tests/test_meal_composition.py` with 8 passing tests.