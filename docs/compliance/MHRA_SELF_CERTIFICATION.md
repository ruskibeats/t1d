# MHRA Self-Certification — T1D Companion

> **Document Version:** 1.0.0  
> **Date:** 2026-05-25  
> **Classification:** Public  
> **Route:** UKCA Class I self-certification (UK MDR 2002, SI 2023 No. 191)

---

## 1. Device Description

**Product Name:** T1D Companion  
**Manufacturer:** (To be registered with MHRA)  
**Intended Purpose:** Educational conversational AI companion for Type 1 Diabetes that:

- Connects to CGM/sensor data (Dexcom, Libre, Nightscout via user authorization)
- Analyzes meals, exercise, stress, alcohol, and sleep impact on glucose patterns
- Provides statistical pattern detection (post-meal spikes, overnight lows, dawn phenomenon)
- Offers **educational insights** based on the user's historical data

**Positioning:** This is an **educational tool**, NOT a medical device. It does NOT:
- Diagnose diabetes or any medical condition
- Provide insulin dosing recommendations
- Replace professional medical advice
- Interface with insulin pumps or other treatment delivery systems
- Make therapeutic recommendations

### 1.1 Intended User

People living with Type 1 Diabetes (T1D) who want to understand their glucose patterns better. Not intended for:
- Children under 16 without guardian supervision
- Users with severe hypo unawareness (as a sole monitoring tool)
- Clinical decision-making by healthcare professionals
- Emergency response

---

## 2. Classification Rationale

### 2.1 UK MDR 2002 Classification Rule

The T1D Companion is classified as **Class I** under Schedule 1 of the UK Medical Devices Regulations 2002 (SI 2002 No. 618, as amended by SI 2023 No. 191).

| Rule | Assessment | Outcome |
|------|-----------|---------|
| Rule 1 (non-invasive) | The software does not penetrate the body. Data is received via authorized APIs (Dexcom, Nightscout) or manual user entry. | **Class I** |
| Rule 3a (invasive) | No connection to the body or bodily fluids. | Not applicable |
| Rule 9 (active therapeutic) | No therapeutic or diagnostic claims. Outputs are explicitly educational observations, not clinical recommendations. | Not applicable |
| Rule 10a (diagnostic) | The companion does not diagnose, monitor for clinical decision-making, or determine treatment. It provides educational pattern observations only. | Not applicable |
| Rule 11 (software) | Software that drives a device or influences the use of a device is classified per the host device. T1D Companion does not connect to any medical device (CGM data is read-only via APIs). | **Class I** — standalone educational software |

### 2.2 Software Qualification per MHRA Guidance

Per MHRA "Medical device stand-alone software including apps" guidance (2022):

- **Do you intend the software to be used for a medical purpose?**  
  No. The purpose is educational insight and pattern observation.

- **Does the software perform an action on data that calculates, interprets, or transforms for a clinical purpose?**  
  No. The software shows historical patterns and educational estimates, explicitly framed as "not medical advice."

- **Is the software an accessory to a medical device?**  
  No. CGM data is consumed via read-only APIs. The software does not modify device behavior.

**Conclusion:** T1D Companion qualifies as **educational software**, not a medical device. However, we pursue voluntary Class I self-certification as a best practice to demonstrate regulatory awareness and patient safety.

---

## 3. Safety Framework

### 3.1 Architecture

```
User Input → SafetyScaffold (keyword scan)
                  ↓
           LLM Service (prompt with guardrails)
                  ↓
           SafetyScaffold (post-LLM validation)
                  ↓
           Disclaimer enforcement
                  ↓
           ForecastSafetyValidator (forecast output)
                  ↓
           User-facing response
```

### 3.2 Guardrails Implemented

| Layer | Mechanism | File |
|-------|-----------|------|
| **Pre-LLM** | Emergency keyword detection (diabetes, mental health, general medical) | `app/ai/safety.py` |
| **Pre-LLM** | Forbidden phrase blocking (dosing language) | `data/safety_config.json` |
| **In-LLM** | System prompt constraints: "Never provide exact dosing" | `app/services/llm_service.py` |
| **Post-LLM** | Policy violation regex (dosing advice, treatment plan changes) | `app/ai/safety.py` |
| **Post-LLM** | Disclaimer enforcement (canonical disclaimer appended if missing) | `app/agents/coordinator.py` |
| **Forecast** | Forecast output validation (evidence text sanitized for dosing language) | `app/services/forecast_safety_validator.py` |

### 3.3 Config-Driven Safety Policy

All safety keywords, dosing regex patterns, and guardrail templates are stored in `data/safety_config.json` (version 2 schema). This allows:

- **Non-engineer review**: Clinicians and legal teams can review keywords without reading Python code
- **Audit trail**: Config file versioning provides change history
- **Override**: Hard-coded defaults serve as safety net if config file is missing

**Config file location:** `/root/t1d/data/safety_config.json`

### 3.4 Emergency Keyword Categories

| Category | Example Keywords | Response |
|----------|-----------------|----------|
| Diabetes emergency | "severe low", "unconscious", "diabetic ketoacidosis", "bg 600" | Escalate: recommend emergency services immediately |
| Mental health crisis | "kill myself", "suicide", "self harm" | Escalate: provide crisis hotline information |
| General medical | "chest pain", "unresponsive", "emergency room" | Escalate: recommend professional help |
| Dosing advice | "take X units", "inject Y", "dose of Z" | Block: replace with educational disclaimer |
| Treatment plan change | "stop insulin", "change treatment" | Block: replace with healthcare provider referral |

### 3.5 Prohibited Outputs

The system **never** produces:

- ❌ Insulin dosing instructions ("take 4.1 units")
- ❌ Treatment plan changes ("stop your basal insulin")
- ❌ Correction factor calculations
- ❌ Carb ratio adjustments
- ❌ Clinical diagnoses

The system **always** produces:

- ✅ "Similar meals used X units on average" (historical data only)
- ✅ "Educational estimate: X units based on similar meals" 
- ✅ "Consider discussing these patterns with your healthcare team"
- ✅ Educational disclaimer with every response

---

## 4. Disclaimer Language

### 4.1 Canonical Disclaimer

```
This application provides educational insights based on your data.
It does not diagnose, treat, or prescribe. Always consult your
healthcare provider before making treatment decisions.
```

### 4.2 Placement

- **API root endpoint (`GET /`)**: Included in response metadata
- **Every chat response**: Appended automatically by `SafetyAgent` if missing from LLM output
- **Forecast responses**: Included via `FORECAST_DISCLAIMER` constant
- **Meal analysis**: Included in all observation outputs

### 4.3 LibreLinkUp Specific Disclaimer

When using the LibreLinkUp integration (reverse-engineered API):

> "This integration is unofficial and not endorsed by Abbott. Use at your own risk.
> Consider using Nightscout (open source, self-hosted) for a supported integration."

---

## 5. Data Protection (GDPR)

### 5.1 Data Collected

| Data Type | Purpose | Retention |
|-----------|---------|-----------|
| CGM glucose readings | Pattern analysis, educational insights | 90 days (configurable) |
| Logged meals (food entries) | Historical meal matching | 90 days |
| Exercise, sleep, mood entries | Cross-domain pattern detection | 90 days |
| User profile (diabetes type, target range) | Personalization | Until account deletion |
| Conversation history | Context for AI responses | 30 days |

### 5.2 GDPR Compliance Measures

- **Data storage**: UK/EU preferred. Right to erasure supported via account deletion API.
- **Data minimization**: Only essential health data stored. No raw LLM training data retention.
- **Consent**: Clear consent for medical data processing at account creation.
- **Right to access**: Users can export their data via API.
- **Right to erasure**: `DELETE /user/{id}` removes all personal data.
- **Data portability**: All data available via REST API.
- **Breach notification**: (To be implemented — Phase 3).

### 5.3 Third-Party Data Processors

| Processor | Data Shared | Purpose |
|-----------|------------|---------|
| OpenRouter / OpenAI | User query + CGM context (anonymized) | LLM response generation |
| OpenFoodFacts | Food search queries | Nutrition data lookup |
| Dexcom (optional) | OAuth token (read-only) | CGM data access |
| Nightscout (optional) | Nightscout URL | CGM data access |

---

## 6. Risk Assessment

### 6.1 Risk Matrix

| Risk | Likelihood | Severity | Mitigation |
|------|-----------|----------|------------|
| LLM produces dosing advice | Low | Critical | Post-LLM safety validation, keyword regex blocking, config-driven pattern updates |
| Emergency keyword missed | Low | Critical | Multiple keyword categories, config file editable by clinicians |
| Incorrect nutrition data | Medium | Moderate | Source trust tiers (verified > official > community > estimated), quality flags, confidence scoring |
| Historical data misinterpreted | Low | Moderate | All forecasts labelled "educational insight, not medical advice" |
| Data breach | Low | Critical | Encryption at rest, API authentication, minimal data collection |

### 6.2 Risk Control Measures

1. **Multi-layer safety validation** — every response passes through at least 2 safety checkpoints
2. **Config-driven policy** — keywords and patterns editable without code deployment
3. **Failsafe defaults** — hard-coded defaults activate if config file is missing or corrupted
4. **Educational framing** — all outputs explicitly labelled as educational, not medical
5. **Confidence scoring** — users see data quality indicators so they can assess reliability

---

## 7. Clinical Evaluation

### 7.1 Exemption Rationale

Per Annex IX of UK MDR 2002, a full clinical investigation is **not required** because:

- The product is educational, not diagnostic or therapeutic
- It does not influence clinical decision-making
- It does not replace or modify existing treatment
- Outputs are explicitly observational ("similar meals used X units on average")
- The user's existing care plan and healthcare provider relationship remain unchanged

### 7.2 Validation Approach

The system is validated through:

1. **Unit tests** — 150+ tests across all safety, forecast, and data modules
2. **Safety test suite** — 32 dedicated safety validation tests
3. **Historical data validation** — 3,251 meal records calibrated against HUPA-UCM and OhioT1DM research datasets
4. **Scenario testing** — 12 anchor profiles tested against expected glucose trace characteristics

---

## 8. Post-Market Surveillance Plan

### 8.1 Monitoring

- **Automated**: Safety violation logging (all blocked responses logged with reason)
- **Manual**: Periodic review of safety logs by designated clinical safety officer
- **User feedback**: In-app mechanism for reporting concerns (to be implemented — Phase 3)

### 8.2 Reporting

- **Serious incidents**: Report to MHRA within 2 calendar days
- **Non-serious incidents**: Report within 30 days
- **Trend analysis**: Monthly safety log review
- **FSN (Field Safety Notice)**: Issued if systemic issue identified

---

## 9. Registration Steps

| Step | Action | Timeline | Cost |
|------|--------|----------|------|
| 1 | Register with MHRA as device manufacturer | Day 1 | £0 |
| 2 | Appoint UK Responsible Person (if manufacturer outside UK) | Day 1 | Variable |
| 3 | Compile technical documentation (this document) | Days 1-5 | £0 |
| 4 | Implement ISO 13485 QMS (or equivalent) | Weeks 1-4 | £0-5K |
| 5 | Register device with MHRA | After QMS | £0 (free for Class I) |
| 6 | Affix UKCA marking | After registration | £0 |
| 7 | Issue Declaration of Conformity | After registration | £0 |
| 8 | Post-market surveillance plan active | Ongoing | £0 |

**Total estimated cost**: £0-5,000 (depending on QMS approach)

---

## 10. Document References

| Document | Location |
|----------|----------|
| Safety configuration (keywords, patterns, guardrails) | `data/safety_config.json` |
| Safety scaffold implementation | `app/ai/safety.py` |
| Forecast safety validator | `app/services/forecast_safety_validator.py` |
| Coordinator with disclaimer enforcement | `app/agents/coordinator.py` |
| Food provenance and confidence model | `app/food/provenance.py` |
| Confidence scoring service | `app/services/confidence_scoring_service.py` |
| Historical meal matching | `app/services/historical_meal_matcher.py` |
| Meal forecast engine | `app/services/meal_forecast_engine.py` |
| LLM service with safeguard prompts | `app/services/llm_service.py` |
| Safety test suite (32 tests) | `tests/ai/test_safety.py` |
| CONTEXT.md (domain language) | `docs/CONTEXT.md` |
| Knowledge base (architecture decisions) | `.agents/skills/t1d-companion-knowledge-base/SKILL.md` |
| Architecture ADRs | `docs/adr/` |

---

## 11. Declaration of Conformity (Template)

```
T1D Companion — Declaration of Conformity

Manufacturer: [Company Name]
Address: [Registered Address]

Product: T1D Companion (software application)
Classification: Class I (per UK MDR 2002 Schedule 1)

We declare under our sole responsibility that the product identified 
above conforms with the relevant provisions of:

- UK Medical Devices Regulations 2002 (SI 2002 No. 618, as amended)
- General Safety and Performance Requirements (Schedule 2, Part I)

Technical documentation is held at [Address] and available upon 
request to the MHRA.

Signed: ________________________
Name: ________________________
Date: ________________________
```

---

*This document is a template for MHRA Class I self-certification. 
It should be reviewed by a qualified regulatory affairs professional 
before submission.*