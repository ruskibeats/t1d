#172 E1-F1: Define MealForecastRequest/Response Pydantic schemas

**Objective**  
Define the canonical typed API contract for meal forecasting so all later services and clients depend on one stable request/response structure. This is the foundation task for the whole feature. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)

**Scope**
- Request schema.
- Response schema.
- Supporting enums and nested types.

**Implementation steps**
1. Define request model with:
   - user_id
   - meal timestamp
   - meal items
   - quantity/unit
   - timezone
   - optional current glucose
   - optional notes/context
2. Define nested response models for:
   - nutrient totals
   - personal context summary
   - forecast windows
   - risk/confidence
   - evidence
   - safety flags
   - narrative
3. Add enums for risk and confidence tiers.
4. Add schema examples based on the current prototype meal format. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/78805486/527fd17c-3c67-48ed-a1ff-c77c66e52a4a/paste.txt)
5. Add validation tests and serialization tests.

**Acceptance criteria**
- Schema is versionable and documented.
- Same models are used by endpoint, persistence layer, and iOS client contracts.
- No loose dicts remain in the main path.

**Done when**
- Meal forecasting has a formal backend contract.