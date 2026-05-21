---
name: frontend-validation-gap-handler
description: "Handle frontend validation gaps discovered during API reviews: identify POST/PUT requests with empty bodies, locate corresponding frontend components, create follow-up tasks with proper verification. Use when frontend code sends {} while backend expects structured data."
version: 1
created: 2026-05-20
updated: 2026-05-20
---
## When to Use
Use this skill when discovering frontend validation gaps where API calls send empty objects instead of structured data, typically found during:
- Code review sessions
- Grill-me verification passes
- API contract audits
- Frontend-backend mismatch detection

## Procedure
1. **Identify the gap**: Find POST/PUT calls with `{}` or missing body fields
2. **Locate frontend component**: Trace the API call to its source component (e.g., Patterns.tsx)
3. **Determine expected fields**: Check API schema or backend model for required fields
4. **Create follow-up task** with:
   - Specific file and line reference
   - Expected vs actual payload description
   - Verification steps (test the endpoint with proper data)
5. **Prioritize appropriately** based on impact (validation gaps often affect data integrity)

## Pitfalls
- Don't assume all empty bodies are bugs (some endpoints may accept optional bodies)
- Verify the gap affects actual behavior, not just test code
- Distinguish between runtime validation and type-checking issues
- Check if the gap is in test fixtures vs production code

## Verification
- FE component sends required fields on API call
- Backend accepts the request without 422 validation errors
- Tests pass with proper payload
- Type checking passes (if TypeScript)