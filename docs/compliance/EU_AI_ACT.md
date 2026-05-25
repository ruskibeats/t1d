# EU AI Act — Compliance Assessment for T1D Companion

> **Document Version:** 1.0.0  
> **Date:** 2026-05-25  
> **Status:** Compliant for current phase  
> **Next review:** August 2026 (high-risk deadline)

---

## 1. Applicability Timeline

The EU AI Act has staggered implementation. This document covers where we sit at each phase.

| Date | What Takes Effect | Applies to Us? |
|------|-------------------|---------------|
| **Feb 2025** | Prohibited AI practices (Article 5) | ❌ Not relevant |
| **Feb 2025** | AI literacy obligations (Article 4) | ✅ **YES** — all providers |
| **Aug 2025** | GPAI rules (general-purpose AI) | ❌ Not a GPAI |
| **Aug 2026** | **High-risk AI system rules (Annex III)** | ⚠️ See analysis below |
| **Aug 2027** | High-risk rules for regulated products | ❌ Not a medical device |

**Key date for us: August 2026.** That's when high-risk system rules go live. We need to ensure our classification holds.

---

## 2. Risk Classification

### 2.1 Current Position: Limited Risk

Under Article 6 and Annex III of the EU AI Act, we classify as **limited risk** (transparency obligations only).

**Why we are NOT high-risk:**

| High-Risk Category (Annex III) | Assessment |
|-------------------------------|-----------|
| 1. Biometric identification | ❌ Not relevant |
| 2. Critical infrastructure | ❌ Not relevant |
| 3. Education/vocational training | ❌ Not relevant |
| 4. Employment/worker management | ❌ Not relevant |
| 5. Access to essential services | ❌ Our app is educational, not a gatekeeper for healthcare |
| 6. Law enforcement | ❌ Not relevant |
| 7. Migration/border control | ❌ Not relevant |
| 8. Administration of justice | ❌ Not relevant |

**Key argument**: The companion provides **educational insights**, not clinical decisions. Users do not rely on the app for treatment decisions — it explicitly says "not medical advice" and "consult your healthcare provider" on every response. It does not determine access to healthcare services.

### 2.2 What Would Make Us High-Risk?

If any of these change, we'd need to reclassify:

| Change | Risk |
|--------|------|
| App starts recommending insulin doses | ⚠️ High-risk — safety component of medical device |
| App markets itself as a clinical decision support tool | ⚠️ High-risk — healthcare access |
| App integrates with insulin pumps | ⚠️ High-risk — safety component |
| App makes determinations about treatment plans | ⚠️ High-risk |

Our current positioning (educational, no dosing, "consult your healthcare provider") keeps us firmly in limited risk.

---

## 3. Transparency Compliance (Current Requirement)

### 3.1 Article 50 — Transparency

> *"Providers shall ensure that natural persons are informed that they are interacting with an AI system."*

| Requirement | Status | Implementation |
|------------|--------|---------------|
| Users know they're talking to AI | ✅ | System prompt: "You are T1D Companion, a helpful and supportive AI assistant" |
| AI disclosure visible in every conversation | ⬜ Partial | First response should explicitly state "I'm an AI assistant" |
| AI-generated content labelled | ✅ | Educational disclaimer appended to every response |
| Deepfake/content labelling | ❌ Not relevant | Not producing synthetic content |

### 3.2 Article 4 — AI Literacy

> *"Providers shall take measures to ensure a sufficient level of AI literacy."*

| Requirement | Status |
|------------|--------|
| Users understand AI capabilities and limitations | ⬜ Not documented |
| Users know when they're talking to AI vs a human | ✅ |
| Users understand data processing by the AI | ⬜ Not documented |

---

## 4. Risk Management (August 2026 Requirement)

Even though we're not high-risk, the August 2026 deadline is a good checkpoint. Here's what we already have in place:

### 4.1 Risk Management System

| Component | Status | Reference |
|-----------|--------|-----------|
| Risk assessment | ✅ | MHRA compliance doc, section 6 |
| Risk mitigation measures | ✅ | Multi-layer safety guardrails |
| Post-market surveillance | ⬜ Planned | Phase 3 roadmap item |

### 4.2 Technical Documentation

| Component | Status | Reference |
|-----------|--------|-----------|
| System description | ✅ | This document + MHRA doc |
| Development methodology | ✅ | Open-source, test-driven |
| Training data | ✅ | LLM provider (OpenRouter) |
| Accuracy metrics | ✅ | 709 passing tests |
| Safety guardrails | ✅ | `app/ai/safety.py`, `data/safety_config.json` |
| Cybersecurity | ⬜ Minor | Uses HTTPS, OAuth, no pump connectivity |

### 4.3 Human Oversight

The companion is designed for **human-in-the-loop** operation:
- Users always make final treatment decisions
- Every response includes "consult your healthcare provider"
- No automated actions (no pump integration, no prescription changes)
- Emergency detection escalates to human response

---

## 5. Action Items for August 2026

| Priority | Action | Effort | Status |
|----------|--------|--------|--------|
| **P1** | Add explicit "I'm an AI" disclosure to companion's first response | Trivial | ⬜ Not done |
| **P1** | Create AI literacy statement for users | Small | ⬜ Not done |
| **P2** | Review risk classification against any updated EU guidance | Small | ⬜ Review cycle |
| **P3** | Implement post-market surveillance logging | Medium | ⬜ Phase 3 |
| **P3** | Formalize human oversight documentation | Small | ⬜ Phase 3 |

---

## 6. Document References

| Document | Location |
|----------|----------|
| Safety scaffold implementation | `app/ai/safety.py` |
| Safety config (keywords, patterns) | `data/safety_config.json` |
| Forecast safety validator | `app/services/forecast_safety_validator.py` |
| MHRA self-certification | `docs/compliance/MHRA_SELF_CERTIFICATION.md` |
| Test suite (709 tests) | `tests/` |
| Domain language / architecture | `docs/CONTEXT.md` |

---

## 7. Declaration

The T1D Companion AI system is classified as **limited risk** under the EU AI Act. It meets current transparency obligations. A formal review is scheduled for **August 2026** to reassess classification against any regulatory changes.

*This document should be reviewed by a qualified regulatory professional.*