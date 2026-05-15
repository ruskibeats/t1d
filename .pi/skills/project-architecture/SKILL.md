---
name: project-architecture
description: T1D Companion architecture, safety, agent workflow, API, data model, and service-boundary guidance. Manual invocation only.
disable-model-invocation: true
---

# Project Architecture Skill

Use this skill when work touches the T1D Companion architecture, including agents, APIs, services, database models, LLM/RAG behavior, frontend data flows, or safety rules.

## Load first

- `references/domain-rules.md` for T1D-specific safety and product rules.
- `scripts/inspect.sh` when you need a quick repo health and structure snapshot.

## Core architecture rules

1. **Safety first**: safety checks happen before data retrieval, pattern analysis, and LLM response generation.
2. **Educational only**: produce pattern observations, not medical decisions.
3. **Keep boundaries clean**:
   - API validation and HTTP behavior: `app/api/`
   - Business logic and integrations: `app/services/`
   - Runtime orchestration: `app/agents/`
   - Database tables: `app/db/models.py`
   - Pydantic request/response schemas: `app/models/`
   - Frontend app: `frontend/src/`
4. **Ground LLM outputs** in retrieved glucose/events/pattern context. Avoid unsupported claims.
5. **Auditability matters**: important safety, sync, and LLM actions should be loggable.

## Runtime agent flow

Expected chat flow:

```text
SafetyAgent -> DataIngestionAgent -> PatternAgent -> ConversationAgent -> optional SummaryAgent
```

Do not bypass SafetyAgent for user-entered messages.

## Implementation preferences

- Prefer small typed functions and explicit return schemas.
- Add tests or smoke checks for safety-sensitive behavior.
- Keep prompts and disclaimers centralized where practical.
- Avoid broad rewrites unless required.

## Before delivery

Use `.pi/prompts/delivery-checklist.md` and summarize changed files.
