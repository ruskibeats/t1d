# ADR 001: Agent Coordinator Architecture

## Status
Accepted

## Context

The T1D Companion system requires multiple specialized agents to handle different domains of diabetes management: data ingestion from CGM devices, pattern detection in glucose data, natural language conversation with users, safety monitoring, and report generation. These agents need to work together in a coordinated pipeline while maintaining clear separation of concerns.

## Decision

We adopted a **Coordinator Pattern** with specialized in-process agents, managed by a central `AgentCoordinator` class.

### Architecture

```
User Message
    │
    ▼
SafetyAgent (emergency check)
    │
    ▼
DataIngestionAgent (fetch glucose, events)
    │
    ▼
PatternAgent (analyze trends, spikes)
    │
    ▼
ConversationAgent (LLM + RAG response)
    │
    ▼
SummaryAgent (format for persistence)
    │
    ▼
Response to User
```

### Agent Responsibilities

| Agent | Responsibility | Key Methods |
|-------|---------------|-------------|
| **DataIngestionAgent** | CGM + meal tracker data | `get_context()` |
| **PatternAgent** | Glucose pattern detection | `analyze_for_conversation()` |
| **ConversationAgent** | LLM + RAG responses | `generate_response()` |
| **SafetyAgent** | Emergency keyword detection | `check_safety()` |
| **SummaryAgent** | Clinic-ready reports | `summarize()` |

### Safety Guardrails

- Emergency keyword detection bypasses normal pipeline
- Content filtering pre-LLM and post-LLM
- All responses include educational disclaimers
- No autonomous insulin dosing recommendations

## Consequences

### Positive
- Clear separation of concerns per agent
- Easy to test individual agents in isolation
- Safety checks are centralized and mandatory
- Pipeline is sequential and predictable

### Negative
- In-process agents share memory space (no process isolation)
- Single point of failure in the coordinator
- Not horizontally scalable without significant refactoring

## Future Considerations

- Migrate to pi-subagents for process isolation and parallel execution
- Add async agent execution for independent tasks
- Implement agent health checks and automatic failover
- Consider event-driven architecture for agent communication

## References

- `app/agents/coordinator.py` — Main coordinator implementation
- `app/services/llm_service.py` — LLM integration
- `app/services/pattern_service.py` — Pattern analysis
- `app/ai/safety.py` — Safety scaffold

---
*Created: 2026-05-18*
