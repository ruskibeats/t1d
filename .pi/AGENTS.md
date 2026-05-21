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

## Clanker Ops

Clanker Ops is the project work queue, planning surface, and shutdown/reporting system. When the user asks to learn, understand, remember, add to, plan, report, summarize, dispatch, queue, or review Clanker Ops work, do **not** create skills, memory files, README files, tools, scripts, or other persistent artifacts unless the user explicitly asks for that artifact or destination.

Default behavior:

- Inspect `.pi/todo-state.json`, `.pi/todo-plans/`, and the Clanker Ops extension only as needed.
- Answer the user directly, or add/update a Clanker Ops work item with a mini-plan.
- Use `/clanker`, `/clanker eod`, `/clanker lights-off`, or the existing Clanker Ops tool actions.
- Leave support artifacts such as skills, tools, scripts, and files to the assigned clanker during dispatch, unless the mini-plan explicitly says to use them.

Examples:

- "learn clanker ops" means inspect and explain the current queue system; it does not mean create a skill.
- "add end of day report to clanker ops" means add/update a Clanker Ops work item with a mini-plan unless the user explicitly asks to implement immediately.
- "add list all .md files in docs folder and add a review todo to clanker ops" means inspect docs as needed, then add the review work item to Clanker Ops.

## Delivery expectations

Before final response, use `.pi/prompts/delivery-checklist.md` as a delivery checklist. Keep responses concise and list changed files clearly.
