---
name: "t1d-post-llm-safety-guardrails"
description: "Implement the 3-layer safety model (pre-LLM, LLM system prompt, post-LLM) for T1D Companion with regulatory documentation. Covers SafetyAgent → SafetyScaffold delegation, policy violation detection (dosing advice, treatment changes), disclaimer enforcement, emergency keyword handling, streaming endpoint safety, and FDA/HIPAA SAFETY.md. Use when implementing or updating safety guardrails for the AI health companion."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Post-LLM Safety Guardrails for AI Health Companion

## When to Use
- Implementing or updating safety guardrails in a T1D Companion chat pipeline
- Adding post-LLM validation (checking LLM output before sending to user)
- Creating FDA/HIPAA regulatory documentation (SAFETY.md)
- Refactoring SafetyAgent to eliminate duplicate keyword lists with SafetyScaffold
- Adding disclaimer enforcement for long educational responses
- Ensuring streaming endpoints are also safety-checked

Do NOT use for:
- Graph-specific RAG safety testing — use `graph-safety-rag-testing` skill instead
- Writing individual safety tests — use standard pytest patterns
- Initial project setup or dependency installation

## Procedure

### 1. Define the Safety Architecture (3-Layer Model)

Document the three-layer safety model in a central reference (e.g., SAFETY.md):

```
Layer 1: Pre-LLM Safety — checks user message before LLM is called
Layer 2: LLM System Prompt — guardrails baked into the system prompt
Layer 3: Post-LLM Safety — validates LLM output before sending to user
```

For each layer, define:
- What it checks (keywords, patterns, policies)
- What action it takes (block + replace, append disclaimer, escalate)
- Which component implements it (SafetyAgent, LLMService, coordinator)

### 2. Create/Update Safety Documentation (docs/SAFETY.md)

Cover:
- **Executive Summary**: Not a medical device, educational tool only
- **Regulatory Framework**: FDA SaMD classification, HIPAA considerations, IMDRF framework
- **Allowed vs prohibited functions**: Use the FDA's explicit examples from mobile health app guidance
- **Three-Layer Architecture**: Diagram and description of each layer
- **Emergency Protocols**: Diabetes emergencies, mental health crisis, general medical emergencies
- **AI Response Guidelines**: Required phrasing ("educational insights suggest"), required disclaimers, critical prohibitions (no dosing, no treatment changes)
- **Implementation files**: List all safety-related files and their purposes
- **Testing requirements**: Categories and coverage

### 3. Implement Pre-LLM Safety (users → LLM)

In the agent coordinator's `process_chat_message()`:
```python
safety_result = await self.agents["safety"].handle({
    "content": message,
    "content_type": "user_message",
    "user_id": user_id,
})
if not safety_result.get("is_safe", False):
    return {"error": "safety_violation", "message": safety_result.get("message")}
```

### 4. Implement Post-LLM Safety (LLM → users)

After LLM generates a response, check it before returning:
```python
post_safety = await self.agents["safety"].handle({
    "content": response_text,
    "content_type": "assistant_response",
    "user_id": user_id,
})
if not post_safety.get("is_safe", True):
    response["response"] = safe_fallback_text  # Replace unsafe content
```

### 5. Implement Disclaimer Enforcement

Define a list of required disclaimer substrings:
```python
DISCLAIMERS = [
    "educational insight", "educational information",
    "not medical advice", "consider discussing",
    "consult your health", "discuss with your",
]
```

After post-LLM safety check passes, check if long responses (e.g., >200 chars) include a disclaimer. If not, append one:
```python
if len(response_text) > 200 and not any(d in response_text.lower() for d in DISCLAIMERS):
    response["response"] = response_text.rstrip() + (
        "\n\n---\n"
        "*This is educational information, not medical advice. "
        "Consider discussing these patterns with your healthcare team.*"
    )
```

### 6. Refactor SafetyAgent → SafetyScaffold Delegation

To eliminate duplicate keyword lists:
- Move all keyword detection, policy violation, and disclaimer logic to a `SafetyScaffold` class (in `app/ai/safety.py`)
- Have `SafetyAgent.handle()` delegate to `SafetyScaffold` methods
- The agent becomes a thin wrapper that receives data dicts and delegates to the scaffold

### 7. Handle Streaming Endpoints

Streaming endpoints need the safety check before the first chunk is streamed, not after:
- Generate the full response (or a preview) first
- Check safety
- If safe, stream the response
- If unsafe, stream the fallback message instead

### 8. Write Safety Tests

Cover at minimum:
- **Emergency keyword detection**: All emergency categories (diabetes, mental health, general medical)
- **Dosing advice block**: Multiple dosing formats ("take X units", "correct with Y units")
- **Treatment change block**: Medication changes, dosage changes
- **Disclaimer enforcement**: Missing disclaimer appended, present disclaimer not duplicated
- **Pipeline post-LLM safety**: Full pipeline blocks unsafe content
- **Stream endpoint safety**: Streaming doesn't bypass safety
- **No false positives**: Educational content about general diabetes knowledge should pass
- **Content format variants**: Keyword detection across plain text, HTML, markdown

Use `pytest` fixtures to mock the LLM service and avoid real API calls in tests.

## Pitfalls

- **Don't skip streaming safety**: Streaming endpoints must safety-check before the first chunk. A naive implementation checks after streaming already started, which means unsafe content escapes.
- **Disclaimer placement varies by response length**: Very short responses (>200 chars) don't need a disclaimer. Longer responses always need one. Use a threshold.
- **False positives on educational content**: "The standard of care for T1D involves..." is safe. "You should take 3 units" is not. Use exact pattern matching + context length heuristics, not simple keyword grep.
- **Dosing advice has many formats**: "take 2 units", "correct with 1u", "give yourself 3U", "bolus 0.5". Test variations.
- **Don't rely solely on system prompt guardrails**: LLMs can be jailbroken. Always validate post-generation.
- **Emergency responses must not triage**: Never try to assess severity. Directly recommend 911/emergency services.
- **Logging sensitivity**: Safety violations contain user medical data. Log at WARNING level, don't log full message content in production.
- **Safety tests are safety-critical themselves**: If tests are wrong or incomplete, safety gaps go undetected. Review test coverage during code review.

## Verification

- `pytest tests/ai/test_safety.py -v` — all 27+ safety tests pass
- `pytest tests/test_chat_pipeline.py -v` — pipeline integration tests pass
- Manually test emergency keywords: "severe low blood sugar" triggers emergency response
- Manually test dosing advice: "take 3 units of insulin" is blocked with safe fallback
- Manually test educational content: "What is the standard of care for T1D?" passes through
- Manually test disclaimer: long educational responses include the educational disclaimer
- `pytest -q` — all tests pass, no regressions
- Verify SAFETY.md covers: executive summary, regulatory framework, 3-layer architecture, emergency protocols, AI response guidelines, implementation files, testing requirements