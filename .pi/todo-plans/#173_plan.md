#173 E2-F1: Build nutrient extraction helper from openfoodfacts_products

**Objective**  
Create a helper that extracts canonical nutrient values from `openfoodfacts_products` into a stable internal format suitable for meal composition and forecasting. The prototype already uses OFF-backed totals; this task formalizes that extraction. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)

**Scope**
- Nutrient field mapping.
- Canonical internal nutrient object.
- Missing-data handling.

**Implementation steps**
1. Inspect `openfoodfacts_products` columns and document nutrient mappings.
2. Define internal nutrient object:
   - carbs_g
   - fiber_g
   - sugars_g
   - protein_g
   - fat_g
   - calories_kcal
   - serving_weight_g
3. Implement extractor with null/zero handling and basis awareness.
4. Add tests using representative OFF rows.
5. Ensure extraction does not embed source-specific assumptions outside the helper.

**Acceptance criteria**
- Helper returns canonical nutrient object from OFF rows.
- Missing fields are explicit.
- Output is ready for serving normalization and provenance scoring.

**Verification**
- Test extractor against known OFF rows. ✓
- Confirm missing values handled gracefully. ✓
- Verify nutrient totals match expected values. ✓

**Done when**
- OFF row access is abstracted behind a dedicated extractor.

### Implementation Summary

Created `app/food/nutrient_extractor.py` with:
- `NutrientProfile` dataclass for canonical nutrient values per 100g
- `extract_nutrients_off()` function for explicit null handling
- `extract_nutrients_safe()` function for 0.0 defaults when needed
- `is_complete()` and `has_minimal_data()` helper methods

Created `tests/test_nutrient_extractor.py` with 12 passing tests covering:
- Complete and partial product extraction
- Empty product handling
- Real-world examples (Big Mac, bread)
- Safe extraction with defaults