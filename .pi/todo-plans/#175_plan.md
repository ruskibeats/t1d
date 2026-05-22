#175 E2-F3: Add food provenance/confidence model (barcode match, source quality, serving certainty)

**Objective**  
Represent how trustworthy each resolved food item is so downstream forecast confidence can be evidence-based rather than implied precision. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)

**Scope**
- Provenance model.
- Confidence inputs.
- Integration with normalized food output.

**Implementation steps**
1. Define provenance object: source name, source id, barcode exact match yes/no, serving certainty, source trust tier, quality flags, last updated. ✓
2. Attach provenance to normalized food result. ✓
3. Add confidence scoring heuristic from provenance fields. ✓
4. Surface provenance in debug output and stored evidence. ✓
5. Add tests for exact barcode, fuzzy name match, inferred serving, duplicate candidate. ✓

**Acceptance criteria**
- Every resolved food item has provenance. ✓
- Forecast engine can lower confidence from provenance weaknesses. ✓
- Admin/debug endpoints expose provenance clearly. ✓

**Done when**
- Food trust is explicit, not hidden.

### Implementation Summary

Created `app/food/provenance.py` with:
- `SourceTrustTier` enum (VERIFIED, OFFICIAL, COMMUNITY, ESTIMATED)
- `QualityFlag` enum for data quality issues
- `FoodProvenance` dataclass with confidence_score() and is_reliable() methods
- `compute_provenance()` factory function

Created `tests/test_provenance.py` with 13 passing tests.