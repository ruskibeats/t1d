# T1D Companion Domain Rules

## Product positioning

The T1D Companion is an educational data companion. It helps users interpret their own historical glucose and context patterns. It does not diagnose, prescribe, or replace clinical care.

Recommended phrasing:

- "Your recent data suggests..."
- "This pattern may be worth discussing with your diabetes care team."
- "Based on similar events in your history..."
- "This is educational information, not medical advice."

Avoid phrasing:

- "Take X units."
- "Change your basal to..."
- "Your correction factor should be..."
- "You should skip/take insulin."
- "This confirms you have..."

## Safety boundaries

Never provide autonomous recommendations for:

- Insulin dose amounts
- Correction doses
- Carb ratios
- Basal rate changes
- Pump settings
- Medication changes
- Diagnosis or treatment plans

Allowed educational insights:

- Time-in-range summaries
- Frequency of lows/highs
- Post-meal pattern observations
- Exercise/stress/sleep/alcohol correlation observations
- Questions the user may bring to a clinician
- General safety reminders and escalation language

## Emergency handling

Treat these as urgent/escalation signals:

- Unconsciousness, seizure, cannot wake
- Severe hypo/hyper symptoms
- DKA concern, vomiting with very high glucose, ketones
- Self-harm or suicidal language
- Requests for urgent medical rescue

Emergency response should be direct and conservative:

> If this may be an emergency, call local emergency services now or seek immediate medical care. If severe low glucose is suspected and the person cannot safely swallow, follow your prescribed emergency glucagon plan and call emergency services.

## Data handling

- Minimize PHI in logs and examples.
- Do not add real tokens, credentials, or sample patient identifiers.
- Use synthetic examples in tests and docs.
- Keep source-specific quirks inside integration services when possible.

## Pattern-analysis expectations

Prefer confidence-aware language. Pattern outputs should include:

- Time window used
- Data volume or sample count
- Observed pattern
- Caveats and missing context
- Suggested clinician discussion points, not treatment actions

## LLM/RAG expectations

LLM responses should:

- Reference retrieved context only when available.
- Admit uncertainty when data is sparse.
- Avoid hallucinated readings, meals, insulin, or diagnoses.
- Include safety caveats for clinically significant highs/lows.
