# Safety & Regulatory Compliance

## Executive Summary

**T1D Companion is an educational data companion — NOT a medical device.**  
It provides pattern recognition, educational insights, and conversational support.  
It does not provide medical advice, diagnosis, dosing recommendations, or treatment decisions.

---

## Regulatory Framework

### FDA / Health Canada / MHRA — Software as a Medical Device (SaMD)

Under international guidance (IMDRF SaMD framework), T1D Companion **is not a medical device** because:

| Factor | Our App | Medical Device |
|--------|---------|----------------|
| **Purpose** | Educational insights, pattern recognition | Diagnosis, treatment, prevention, monitoring |
| **Output** | Observational statements, discussion prompts | Specific clinical recommendations |
| **User action** | User discusses with their care team | User acts directly on device output |
| **Dosing** | Never recommends insulin doses | Calculates or recommends doses |
| **Clinical impact** | Informed conversations with HCP | Direct patient management |

### FDA Mobile Health App Guidance

The FDA has provided specific examples of functions that are **NOT** medical devices:

**✅ Allowed (our app):**
- "Educational tools that provide general information about managing a disease"
- "Apps that help patients track their health data and spot patterns"
- "Wellness coaching apps that provide general health recommendations"
- "Apps that organize and trend health data for patient review"
- "Apps that provide reminders for medications established by the HCP"

**❌ NOT Allowed (must avoid):**
- "Apps that calculate insulin dosage or corrective doses"
- "Apps that make specific treatment recommendations based on user data"
- "Apps that diagnose a specific disease or condition"
- "Apps that provide clinical decision support for treatment changes"

### HIPAA / Data Privacy

- **Personal Health Record (PHR)** — Data belongs to the user; HIPBA applies if covered entity
- **Educational tool** — Not a covered healthcare provider
- **Best practice** — Implement HIPAA-level security regardless:
  - Encryption at rest and in transit
  - User-controlled data access
  - No data sharing without explicit consent
  - Right to delete all personal data

---

## Safety Architecture

### Three-Layer Safety Model

```
User Message
    │
    ▼
Layer 1: Pre-LLM Safety (SafetyAgent → SafetyScaffold)
    ├─ Emergency keyword detection
    ├─ Mental health crisis detection
    ├─ General medical emergency detection
    └─ If unsafe → direct response, no LLM call
    │
    ▼
Layer 2: LLM Generation (ConversationAgent → LLMService)
    ├─ System prompt with safety guardrails
    ├─ RAG context grounded in user data
    ├─ Disclaimer baked into prompt
    └─ Educational tone enforced
    │
    ▼
Layer 3: Post-LLM Safety (SafetyAgent → SafetyScaffold)
    ├─ Policy violation detection (dosing, treatment changes)
    ├─ Disclaimer enforcement
    └─ If unsafe → replace with safe fallback
    │
    ▼
Response to User
```

### Layer 1 — Pre-LLM Safety

**What it does:** Scans user messages for safety keywords before the LLM is ever called.

**Scenarios:**
| Detected | Action |
|----------|--------|
| "severe low blood sugar" | Return emergency response + 911 recommendation |
| "I want to hurt myself" | Return crisis hotline + support resources |
| "chest pain" | Return urgent care recommendation |
| Normal query | Pass through to LLM |

### Layer 2 — LLM System Prompt

**What it does:** The system prompt instructs the LLM on:
- Educational-only role (not clinical)
- No dosing advice under any circumstances
- Acknowledge individual variability
- Always include educational disclaimer
- Use observational language ("patterns indicate", "consider discussing")

**Context provided:**
- User's actual glucose data (last 20 readings)
- Recent events (meals, exercise, insulin)
- Pattern analysis (TIR, spikes, overnight lows)
- Graph relationships (observational correlations)
- Safety guardrails (condition-specific)

### Layer 3 — Post-LLM Safety

**What it does:** After the LLM generates a response, validates it before sending to user.

**Policy violations detected:**
| Pattern | Example | Action |
|---------|---------|--------|
| Dosing advice | "Take 3 units" | Block + replace with safe fallback |
| Treatment change | "Stop taking insulin" | Block + replace with safe fallback |
| Medication change | "Switch to this medication" | Block + replace with safe fallback |
| Missing disclaimer | Long response without "educational" | Append disclaimer |
| Emergency keywords | Response mentions self-harm | Block + escalate |

---

## AI Response Guidelines

### Required Phrasing

Always use observational language:

| ✅ Do Say | ❌ Don't Say |
|-----------|-------------|
| "Educational insights suggest..." | "You should..." |
| "Patterns indicate..." | "You need to..." |
| "Consider discussing with your care team..." | "Take this action..." |
| "Some strategies to explore include..." | "What you should do is..." |
| "Based on similar patterns in your data..." | "In your case specifically..." |
| "This is educational information, not medical advice" | *(omit this disclaimer)* |

### Required Disclaimers

Every AI response must include (or be preceded by) one of:
- "This is educational information, not medical advice."
- "Educational insights suggest..."
- "Consider discussing these patterns with your healthcare team."

### Critical Prohibitions

The AI must NEVER:
1. **Give specific insulin doses** ("take 2 units", "correct with 1u")
2. **Suggest medication changes** ("switch to this drug", "stop taking that")
3. **Diagnose conditions** ("you have diabetic ketoacidosis")
4. **Guarantee outcomes** ("if you do this, your glucose will be normal")
5. **Override HCP instructions** ("ignore what your doctor said about...")
6. **Provide treatment plans** ("here's what to do for the next week")
7. **Recommend specific glucose targets** outside the standard range

---

## Implementation

### Files

| File | Purpose |
|------|---------|
| `app/ai/safety.py` | SafetyScaffold class — keyword detection, policy violations, guardrails |
| `app/agents/coordinator.py` | Agent coordinator with pre/post LLM safety |
| `app/services/llm_service.py` | LLM service with safety-constrained system prompt |
| `app/api/chat.py` | Chat endpoints with second safety layer |
| `tests/ai/test_safety.py` | SafetyScaffold unit tests (27+ tests) |
| `tests/test_chat_pipeline.py` | Pipeline-level safety tests |

### Post-LLM Safety Flow

```python
# In coordinator.py — after LLM generates response:
post_safety = await self.agents["safety"].handle({
    "content": response_text,
    "content_type": "assistant_response",
})
if not post_safety.get("is_safe", True):
    response["response"] = safe_fallback_text  # Replaces unsafe content
```

---

## Emergency Protocols

### Diabetes Emergency

Keywords: severe low, can't wake, unconscious, seizure, glucagon, ketoacidosis, over 600

**Response:** 
1. Immediate recommendation to seek emergency care
2. DO NOT provide any medical guidance
3. DO NOT attempt to triage severity
4. Offer non-medical support ("stay with the person", "call 911")

### Mental Health Crisis

Keywords: kill myself, suicide, want to die, self harm, hurt myself

**Response:**
1. Provide crisis hotline: 988 (US) or local equivalent
2. Encourage contacting a trusted person
3. Do NOT minimize or dismiss
4. Do NOT provide clinical diagnosis

### General Medical Emergency

Keywords: chest pain, can't breathe, heart attack, stroke, allergic reaction

**Response:**
1. Recommend immediate emergency care
2. Do not attempt to diagnose or triage
3. Stay supportive but recommend professional help

---

## Testing Requirements

All safety features must be covered by automated tests:

| Test | File | Coverage |
|------|------|----------|
| Emergency keyword detection | `test_safety.py` | All emergency categories |
| Dosing advice block | `test_safety.py` | Multiple dosing formats |
| Treatment change block | `test_safety.py` | Medication changes |
| Disclaimer enforcement | `test_safety.py` | Missing disclaimer |
| Pipeline post-LLM safety | `test_chat_pipeline.py` | Full pipeline |
| Stream endpoint safety | `test_chat_pipeline.py` | Streaming safety |
| No false positives | `test_safety.py` | Educational content |

---

## References

- [FDA: Policy for Device Software Functions and Mobile Medical Apps](https://www.fda.gov/medical-devices/device-software-functions-including-mobile-health-apps/policy-device-software-functions-and-mobile-health-apps)
- [IMDRF SaMD Framework](https://www.imdrf.org/consultations/software-medical-device-samd-key-definitions)
- [HIPAA Journal: Mobile Health Apps](https://www.hipaajournal.com/mobile-health-apps-hipaa/)
- [Diabetes Technology Society](https://www.diabetestechnology.org/)
- [ADA Standards of Medical Care in Diabetes](https://professional.diabetes.org/standards-of-care)

---

**Document version:** 1.0  
**Last updated:** 2026-05-20  
**Review frequency:** Quarterly or upon regulatory changes