# Clanker Ops Plan — #165: Critical safety features — post-LLM validation + regulatory guardrails

## Intended Outcome
AI assistant safely acts as a diabetic coach with full regulatory guardrails. No dosing advice, no treatment changes, no medical diagnosis. Educational disclaimers enforced on all responses. Streaming endpoint protected.

## Step-by-Step
1. Research FDA health app regulations and create `docs/SAFETY.md`
2. Refactor SafetyAgent to delegate to SafetyScaffold (remove duplicate keyword lists)
3. Add disclaimer enforcement to post-LLM check in coordinator.py
4. Fix chat/stream endpoint to check safety before saving/streaming
5. Run full test suite — confirm all 324 tests pass including 30 safety tests
6. Update Clanker Ops board with completion

## Verification
- ✅ 324 tests passing (30 safety-specific)
- ✅ Dosing advice blocked: "take 3 units" → replaced with safe fallback
- ✅ Treatment changes blocked: "stop taking medication" → replaced
- ✅ Disclaimer enforced on long responses without "educational" or "not medical advice"
- ✅ Streaming endpoint checks safety before saving
- ✅ SafetyAgent no longer has duplicate keyword lists (delegates to SafetyScaffold)
- ✅ docs/SAFETY.md documents FDA, HIPAA, and safety architecture

## Dependencies
- docs/SAFETY.md (new)
- app/agents/coordinator.py (modified — SafetyAgent delegate to SafetyScaffold)
- app/agents/coordinator.py (modified — disclaimer enforcement in post-LLM)
- app/api/chat.py (modified — stream endpoint safety check)
- app/ai/safety.py (existing — no changes needed)
- tests/ai/test_safety.py (existing — 30 tests, all pass)

## Audit
- Created: 2026-05-20
- Assigned: @pi
- Status: completed