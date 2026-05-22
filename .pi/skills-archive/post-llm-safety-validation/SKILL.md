---
name: "post-llm-safety-validation"
description: "Implement post-LLM safety validation with regulatory guardrails for health/medical AI chatbots. Covers: three-layer safety architecture (pre-LLM → LLM prompt → post-LLM), keyword/policy violation detection, disclaimer enforcement, streaming endpoint protection, and safety test coverage. Use when building a medical advice guardrail, health AI with dosing/treatment prevention, or educational health companion with FDA/HIPAA awareness."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Post-LLM Safety Validation for Health/Medical AI

## When to Use

Implement post-LLM safety validation with regulatory guardrails for a health or medical AI chatbot. Use when:

- Building any AI system that discusses **health, medical conditions, or treatments** with users
- Implementing a **diabetes companion, wellness coach, or symptom checker** that must avoid giving medical advice
- Adding **safety guardrails** to an existing health-related LLM-powered chat application
- Protecting **streaming chat endpoints** from serving unsafe content
- Preparing for **regulatory compliance** (FDA SaMD guidance, HIPAA best practices)

Do NOT use for:

- Non-health general-purpose chatbots (use generic content filtering instead)
- Medical devices that provide actual clinical decision support (those need formal regulatory clearance)
- Simple profanity/content filters in non-medical contexts

## Procedure

### 1. Understand the regulatory landscape

Before writing code, determine your regulatory posture. Most health companion apps fall under **FDA's Mobile Health App guidance** as educational tools — NOT medical devices.

Key principles to document:

| Factor | Educational Tool (your app) | Medical Device |
|--------|----------------------------|----------------|
| Purpose | Pattern recognition, education | Diagnosis, treatment, monitoring |
| Output | Observational statements | Clinical recommendations |
| Dosing | Never recommends doses | Calculates/recommends doses |
| User action | Discuss with care team | Acts directly on output |

Create a `SAFETY.md` or equivalent doc covering:
- FDA SaMD framework and why your app is not a medical device
- HIPAA data privacy best practices (encryption, user control, right to delete)
- Three-layer safety architecture overview
- Emergency protocols (medical emergencies, mental health crises)
- AI response guidelines (required phrasing, disclaimers, prohibitions)

### 2. Design a three-layer safety architecture

```
User Message
    │
    ▼
Layer 1: Pre-LLM Safety
    ├─ Emergency keyword detection (medical, mental health)
    ├─ If unsafe → direct emergency response, no LLM call
    │
    ▼
Layer 2: LLM Generation
    ├─ System prompt with safety guardrails
    ├─ RAG context grounded in user data
    ├─ Disclaimer baked into prompt
    └─ Educational tone enforced
    │
    ▼
Layer 3: Post-LLM Safety (← THIS SKILL'S FOCUS)
    ├─ Policy violation detection
    ├─ Disclaimer enforcement
    └─ If unsafe → replace with safe fallback
    │
    ▼
Response to User
```

### 3. Build the SafetyScaffold (shared safety logic)

Create a single shared safety module (e.g., `app/ai/safety.py`) that all agents delegate to. This avoids duplicate keyword lists and inconsistent logic.

**Structure:**

```python
class SafetyScaffold:
    """Shared safety logic — one source of truth for all safety checks."""

    EMERGENCY_KEYWORDS: ClassVar[Dict[str, List[str]]] = {
        "medical": [
            "severe low", "can't wake", "unconscious", "seizure",
            "glucagon", "ketoacidosis", "over 600", "er",
            "chest pain", "difficulty breathing", "severe bleeding",
            "emergency room", "hospital",
        ],
        "mental_health": [
            "kill myself", "suicide", "want to die", "self harm",
            "hurt myself", "end it", "give up",
        ],
    }

    POLICY_VIOLATIONS: ClassVar[List[Dict]] = [
        {
            "pattern": r'(?i)\b(take|administer|inject)\s+\d+\.?\d*\s*(units?|u)\b',
            "category": "dosing_advice",
            "message": "Cannot provide specific dosing advice.",
        },
        {
            "pattern": r'(?i)\b(stop|discontinue|cease)\s+(taking|using|your)\s+(insulin|medication)\b',
            "category": "treatment_change",
            "message": "Cannot recommend treatment changes.",
        },
        # Add more patterns as needed
    ]

    @classmethod
    def check_emergency(cls, text: str) -> dict:
        """Layer 1 check — detect emergencies in user messages."""
        ...

    @classmethod
    def validate_post_llm(cls, text: str) -> dict:
        """Layer 3 check — validate LLM responses before sending to user."""
        ...
```

**Key methods:**

- `check_emergency(text)` — scans for medical/mental health emergency keywords; returns `is_safe`, `safety_level`, `reasons`, `requires_escalation`
- `validate_post_llm(text)` — scans for policy violations (dosing advice, treatment changes) and checks disclaimer presence; returns `is_safe`, `violations`, `needs_disclaimer`

### 4. Implement pre-LLM safety (Layer 1)

In your agent coordinator or chat handler, before calling the LLM:

```python
# Check user message for emergencies
pre_safety = SafetyScaffold.check_emergency(user_message)
if pre_safety.get("safety_level") == "emergency":
    return {
        "response": "Please seek immediate medical attention...",
        "safety": pre_safety,
    }
```

### 5. Prepare the safety-constrained LLM system prompt (Layer 2)

The system prompt is your first line of defense for the LLM's output. Include:

```
You are an educational data companion, NOT a medical device.
- Never give specific dosing advice (insulin units, medication amounts)
- Never recommend medication or treatment changes
- Never diagnose conditions
- Never guarantee outcomes
- Never override healthcare provider instructions
- Use observational language: "patterns indicate", "consider discussing", "educational insights suggest"
- Always include an educational disclaimer
```

### 6. Implement post-LLM safety (Layer 3) — the core of this skill

After the LLM generates a response, run it through post-LLM validation:

```python
# In your coordinator or chat handler, AFTER LLM returns a response:
post_safety = SafetyScaffold.validate_post_llm(response_text)
if not post_safety.get("is_safe", True):
    # Replace unsafe content with safe fallback
    safe_fallback = "I'm designed to provide educational insights, not specific medical advice. " \
                    "Please discuss any treatment changes with your healthcare provider."
    response_text = safe_fallback
```

**What to check in post-LLM validation:**

| Check | Pattern | Action |
|-------|---------|--------|
| Dosing advice | "Take 3 units" or equivalent | Block + replace |
| Treatment change | "Stop taking insulin" or equivalent | Block + replace |
| Medication change | "Switch to this drug" | Block + replace |
| Missing disclaimer | Long response without "educational" or "not medical advice" | Append disclaimer |
| Emergency keywords | Response mentions self-harm, crisis | Block + escalate |

**Disclaimer enforcement heuristic:**

```python
DISCLAIMER_PHRASES = [
    "educational insights",
    "not medical advice",
    "educational information",
    "consult your healthcare",
    "discuss with your",
    "consider discussing",
]

def needs_disclaimer(text: str) -> bool:
    """Long responses need at least one disclaimer phrase."""
    if len(text) < 100:
        return False  # Short responses may not need one
    return not any(phrase in text.lower() for phrase in DISCLAIMER_PHRASES)
```

### 7. Protect streaming endpoints

Streaming endpoints are particularly tricky because the response is sent token-by-token. You must check safety BEFORE saving or streaming.

**Stream-safe pattern:**

```python
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, ...):
    # Step 1: Pre-LLM safety on user message
    pre_safety = safety_agent.handle(request.message)
    if not pre_safety["is_safe"]:
        # Return emergency response as a complete response, not streaming
        return StreamingResponse(iter([pre_safety["message"]]), ...)

    # Step 2: Generate full response first (blocking on LLM)
    full_response = await llm_service.generate(...)

    # Step 3: Post-LLM safety on the complete response
    post_safety = safety_agent.handle(full_response, content_type="assistant_response")
    if not post_safety["is_safe"]:
        full_response = safe_fallback_text

    # Step 4: Save the response (now it's safe)
    await save_conversation(...)

    # Step 5: NOW stream it to the user
    async def stream():
        for chunk in chunk_text(full_response):
            yield f"data: {json.dumps({'content': chunk})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
```

**Critical rule:** Never stream a response before validating it. Generate the full response, validate, save, THEN stream.

### 8. Write safety-specific tests

Cover these scenarios:

```python
# Test 1: Dosing advice blocked
assert "take 3 units" in unsafe_response
result = safety_scaffold.validate_post_llm(unsafe_response)
assert not result["is_safe"]

# Test 2: Treatment change blocked
result = safety_scaffold.validate_post_llm("Stop taking your insulin")
assert not result["is_safe"]

# Test 3: Disclaimer appended to long responses
result = safety_scaffold.validate_post_llm(long_response_without_disclaimer)
assert result["needs_disclaimer"]

# Test 4: Safe educational content passes
result = safety_scaffold.validate_post_llm("Educational insights suggest patterns...")
assert result["is_safe"]

# Test 5: Short responses don't need disclaimer
result = safety_scaffold.validate_post_llm("Yes, I understand.")
assert not result["needs_disclaimer"]
```

### 9. Refactor to eliminate duplicate safety logic

If you have multiple agents or handlers doing safety checks:

```python
# BEFORE: SafetyAgent has its own keyword list
class SafetyAgent:
    EMERGENCY_KEYWORDS = [...]  # Duplicated

# AFTER: Delegate to shared SafetyScaffold
class SafetyAgent:
    async def handle(self, data):
        return SafetyScaffold.validate_post_llm(data.get("content"))
```

This ensures one source of truth for safety keywords, patterns, and logic.

## Pitfalls

- **Don't only rely on the system prompt (Layer 2)**: LLMs can be jailbroken or ignore safety instructions. Post-LLM validation (Layer 3) is your safety net. Always validate the actual output, not just the prompt.
- **Streaming + safety is a trap**: The most natural implementation streams LLM tokens directly — but then you can't retroactively block unsafe content because it's already been sent. Always generate the full response, validate, THEN stream or return.
- **Disclaimer phrases need heuristics**: A short "ok" doesn't need a disclaimer. Multi-paragraph medical discussion absolutely does. Use a length threshold (~100 chars) to decide when to enforce.
- **Regular expressions are brittle but necessary**: For policy violation detection, regex is the most reliable approach. Test your patterns against edge cases (e.g., "take 0.5 units of insulin" vs "take notes on your levels").
- **Whitespace and punctuation in disclaimers**: `"educational insights"` in your check won't match `"Educational Insights:"` if case-sensitive. Always lowercase both sides. Account for markdown, bold, italic formatting in responses.
- **Silent replacement confuses users**: When you replace unsafe content, consider prefacing with a brief note: "I can't provide specific medical advice, but here's what I can share: ..."
- **Single safety agent with multiple responsibilities**: Pre-LLM emergency detection and post-LLM policy validation are different concerns. If they're in one class, make sure the `content_type` parameter (user_message vs assistant_response) routes to the right checks.
- **Audit trail**: Log all safety events (pre-LLM blocks, post-LLM replacements, disclaimer appends) with timestamps and the original content (or a hash). Essential for regulatory accountability.

## Verification

1. **Pre-LLM safety**: Send "I can't wake them up" → expect emergency response returned immediately (no LLM call)
2. **Post-LLM dosing**: Force the LLM to generate dosing advice → expect response replaced with safe fallback
3. **Post-LLM treatment change**: Force "stop taking insulin" response → expect blocked
4. **Disclaimer enforcement**: Generate a long response without disclaimer → expect disclaimer appended
5. **Streaming safety**: Stream endpoint must NOT send unsafe content before validation
6. **Short response pass-through**: "Yes" or "I see" → no disclaimer needed
7. **All tests pass**: Full test suite including safety-specific tests
8. **Safety doc exists**: SAFETY.md (or equivalent) covers regulatory framework, architecture, and protocols