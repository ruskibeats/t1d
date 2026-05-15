# Pi Agents for T1D Companion

This directory contains project-local Pi guidance for the Type 1 Diabetes Companion.

## Mission

Build a sensor-agnostic, safety-first educational data companion for T1D. The system helps users understand patterns in CGM, meals, insulin, exercise, sleep, stress, alcohol, illness, and other context data.

## Non-negotiables

- This is **not a medical device**.
- Do **not** provide autonomous insulin dosing, carb-ratio changes, correction-factor changes, basal changes, diagnosis, or treatment instructions.
- Provide educational pattern insights only.
- Encourage the user to discuss significant patterns with their diabetes care team.
- Escalate emergency language to urgent medical care.
- Preserve privacy and avoid unnecessary PHI exposure.

## Project architecture

- Backend: FastAPI in `app/`
- Runtime agents: `app/agents/coordinator.py`
- Services: `app/services/`
- API routes: `app/api/`
- SQLAlchemy models: `app/db/models.py`
- Pydantic schemas: `app/models/`
- Frontend: React/TypeScript in `frontend/src/`
- Documentation: root markdown files and `docs/`

## Local skills

Project-local skills in `.pi/skills/` are configured for **manual invocation only** with `disable-model-invocation: true`. They should not be injected into the startup system prompt.

Use them explicitly when needed:

- `/skill:project-architecture`
- `/skill:qa-smoke-test`

## Delivery expectations

Before final response, use `.pi/prompts/delivery-checklist.md` as a delivery checklist. Keep responses concise and list changed files clearly.
