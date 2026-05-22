#174 E2-F2: Add serving normalization helper for g, ml, slices, pieces

**Objective**  
Normalize food quantities into a canonical gram-based or equivalent representation so nutrient aggregation is correct across different serving formats. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)

**Scope**
- Unit conversion helper.
- Serving inference rules.
- Error handling for ambiguous quantities.

**Implementation steps**
1. Define supported units: g, kg, ml, l, slice, piece, serving, cup, tbsp, tsp, etc. ✓
2. Build conversion helper using food row serving metadata. ✓
3. Add fallback rules when explicit gram weight is missing. ✓
4. Return normalized quantity + confidence/uncertainty. ✓
5. Add tests for bread slices, eggs, liquids, branded serving rows. ✓

**Acceptance criteria**
- Helper returns canonical quantity for common serving types. ✓
- Ambiguous serving sizes degrade confidence rather than guessing silently. ✓
- Bread/slice and piece-based foods are supported reliably. ✓

**Verification**
- Confirm eggs + bread example resolves correctly. ✓

**Done when**
- Quantity normalization is reliable enough for forecast inputs.

### Implementation Summary

Created `app/food/serving_normalizer.py` with:
- `NormalizedQuantity` dataclass with grams, confidence, and notes
- `normalize_quantity()` function for general unit conversion
- `normalize_from_off()` function that prefers product serving data
- DEFAULT_SERVING_WEIGHTS mapping for common units

Created `tests/test_serving_normalizer.py` with 14 passing tests covering:
- Gram/kg direct conversion
- Volume units (ml, cup, tsp, tbsp)
- Countable units (slice, piece, serving)
- OFF product integration
- Real-world examples (eggs, bread, liquids)