# T1D Agent System

This directory contains agent definitions for the T1D Companion system's multi-agent architecture.

## Overview

The T1D Companion uses a multi-agent system combining:
- **Python Runtime Agents** (`app/agents/`) - Production implementation
- **Pi Subagents** (this directory) - AI-assisted development and orchestration

## Architecture

The system uses a coordinator-based multi-agent pattern where specialized agents handle distinct domains:

| Agent | Responsibility | Implementation |
|-------|---------------|----------------|
| **coordinator** | Orchestrates agent workflow and delegates tasks | `app/agents/coordinator.py` |
| **data_ingestion_agent** | Handles CGM/Nightscout data sync and meal tracker integration | `DataIngestionAgent` class |
| **pattern_agent** | Analyzes glucose patterns and correlations | `PatternAgent` class |
| **conversation_agent** | Manages natural language interactions | `ConversationAgent` class |
| **safety_agent** | Enforces guardrails and handles escalation | `SafetyAgent` class |
| **summary_agent** | Generates clinic-ready reports | `SummaryAgent` class |

## Agent Definitions

### Coordinator

**Purpose**: Central orchestrator for all agent operations

**Key Functions**:
- Task delegation and routing
- Pipeline execution (safety → data → pattern → conversation)
- Error handling and fallbacks
- Agent lifecycle management

**Methods**:
```python
async def startup()                          # Initialize all agents
async def shutdown()                         # Graceful shutdown
async def delegate_task(type, data)          # Route to specific agent
async def process_chat_message(msg, user_id) # Full conversation pipeline
```

### DataIngestionAgent

**Purpose**: Handle CGM and meal tracker data ingestion

**Key Functions**:
- Fetch glucose readings from Dexcom/Nightscout
- Retrieve context events (meals, insulin, exercise)
- Provide structured context for conversations

**Methods**:
```python
async def handle({"action": "get_context", "user_id": id})
# Returns: {"glucose": {...}, "events": [...], "patterns": [...]}
```

### PatternAgent

**Purpose**: Detect and analyze glucose patterns and correlations

**Key Functions**:
- Post-meal spike detection
- Overnight hypoglycemia identification
- Exercise effect analysis
- Nutritional impact correlation
- Time-in-range calculations

**Methods**:
```python
async def handle({"action": "analyze_for_conversation", ...})
# Returns: {"patterns": [], "trends": {}, "correlations": []}
```

### ConversationAgent

**Purpose**: Natural language conversation and LLM integration

**Key Functions**:
- Context-aware response generation
- Pattern summarization in plain language
- Multi-turn conversation management
- RAG (Retrieval-Augmented Generation)

**Methods**:
```python
async def handle({
    "message": str,
    "context": {...},
    "patterns": {...}
})
# Returns: {"response": str, "confidence": float, "sources": []}
```

### SafetyAgent

**Purpose**: Safety monitoring, content filtering, and escalation

**Key Functions**:
- Emergency keyword detection
- Content safety validation
- Escalation to medical services
- Audit logging

**Emergency Keywords**:
- Emergency terms: "emergency", "urgent", "help", "911", "hospital"
- Crisis terms: "suicide", "kill myself", "end it"
- Medical terms: "unconscious", "can't wake", "severe"

**Methods**:
```python
async def handle({"content": str, "content_type": str})
# Returns: {"is_safe": bool, "safety_level": str, "requires_escalation": bool}
```

### SummaryAgent

**Purpose**: Generate summaries and clinic-ready reports

**Key Functions**:
- Pattern summaries (time-based)
- Clinic report generation
- Export formatting
- Trend documentation

**Methods**:
```python
async def handle({"format": "text", "time_range": {...}})
# Returns: {"status": "ok", "summary": str, "format": str}
```

## BaseAgent Class

All agents inherit from `BaseAgent`:

```python
class BaseAgent:
    def __init__(self, name: str)
    async def handle(self, data: dict) -> dict
    async def shutdown(self) -> None
```

**Provides**:
- Standardized logging
- Common interface
- Error handling foundation
- Lifecycle management

## Runtime vs Development

### Python Runtime Agents (`app/agents/coordinator.py`)

**Production implementation**:
- In-process coordinator
- FastAPI integration
- Database persistence
- Real-time processing
- Full error handling
- LLM integration

**Used by**: Production application, API endpoints, user-facing features

### Pi Subagents (This Directory)

**Development orchestration**:
- Markdown/YAML definitions
- Separate processes
- AI-assisted development
- Documentation generation
- Planning and review

**Used by**: Claude Code, Pi, development workflows

## Usage Examples

### Python Runtime

```python
from app.agents.coordinator import AgentCoordinator

coordinator = AgentCoordinator()
await coordinator.startup()

# Full pipeline
response = await coordinator.process_chat_message(
    message="Why did I spike?",
    user_id=42
)

# Direct delegation
result = await coordinator.delegate_task(
    "pattern",
    {"action": "analyze_for_conversation", ...}
)

await coordinator.shutdown()
```

### Pi Subagents

```bash
# List agents
pi subagent list

# Run coordinator task
pi subagent single \
  --agent coordinator \
  --task "Review conversation flow"

# Chain multiple agents
pi subagent chain \
  --chain '[{"agent": "pattern_agent"}, {"agent": "conversation_agent"}]'
```

## Data Flow

### Typical User Query

```
1. User Message
   │
   ▼
2. SafetyAgent
   ├─ Check keywords
   ├─ Validate content
   └─ Escalate if needed
   │
   ▼
3. DataIngestionAgent
   ├─ Get glucose readings
   ├─ Fetch events
   └─ Compile context
   │
   ▼
4. PatternAgent
   ├─ Analyze correlations
   ├─ Detect anomalies
   └─ Generate insights
   │
   ▼
5. ConversationAgent
   ├─ Build RAG context
   ├─ Call LLM
   └─ Generate response
   │
   ▼
6. Response to User
```

## Integration Points

### Services

- **DexcomService**: `app/services/dexcom_service.py`
- **NightscoutService**: `app/services/nightscout_service.py`
- **MealService**: `app/services/meal_service.py`
- **PatternService**: `app/services/pattern_service.py`
- **LLMService**: `app/services/llm_service.py`

### API Endpoints

- **Chat**: `app/api/chat.py`
- **Patterns**: `app/api/patterns.py`
- **Events**: `app/api/events.py`
- **Glucose**: `app/api/glucose.py`

## Development

### Adding New Agent

1. Create agent class in `app/agents/`
2. Inherit from `BaseAgent`
3. Implement `handle()` method
4. Register in `AgentCoordinator`
5. Add tests
6. Update documentation

See `DEVELOPMENT.md` for detailed guidelines.

### Testing

```bash
# Run agent tests
pytest tests/unit/test_agents.py -v

# Test coordinator
pytest tests/test_coordinator.py

# Test full pipeline
pytest tests/integration/test_chat_pipeline.py
```

## Documentation

- **System Architecture**: `../SYSTEM.md`
- **Agent Documentation**: `../AGENTS.md`
- **Development Guide**: `../DEVELOPMENT.md`
- **Setup Guide**: `../SETUP.md`

## Safety & Compliance

### Core Principles

1. **Not a Medical Device**: Educational tool only
2. **No Autonomous Dosing**: Never provides insulin recommendations
3. **Clinical Oversight**: Encourages healthcare provider consultation
4. **Data Privacy**: HIPAA-compliant practices
5. **Transparency**: Clear about limitations

### Emergency Handling

When emergency keywords are detected:
- Immediate response with safety message
- Log escalation event
- Recommend seeking medical attention
- Never proceed with normal conversation

## Notes on pi-subagents

This project includes `pi-subagents` as a dev dependency for AI-assisted development workflows.

During development:
- Use pi subagents for code review, planning, testing
- Chain multiple agents for complex tasks
- Leverage specialized skills (design, security, testing)

During runtime:
- Python agents handle all user-facing operations
- Full error handling and logging
- Database persistence
- Production-ready reliability

## Configuration

Agent behavior is configured through:

- **Environment variables**: `LLM_PROVIDER`, `DATABASE_URL`, etc.
- **Settings class**: `app/config.py`
- **Service configs**: Individual service modules

See `.env.example` for all configuration options.

## Troubleshooting

### Agent Not Responding

```bash
# Check coordinator is running
await coordinator.startup()

# Verify agent registration
print(coordinator.agents.keys())
```

### Task Type Unknown

```bash
# Check agent_map in delegate_task()
# Ensure mapping exists for task type
```

### Import Errors

```bash
# Install dependencies
pip install -e .

# Check Python version (3.11+ required)
python --version
```

## License

TBD - pending legal review

## Disclaimer

**This is a research project and not a medical device. It does not provide medical advice, diagnosis, or treatment recommendations. Always consult with your healthcare provider regarding diabetes management and treatment decisions.**

