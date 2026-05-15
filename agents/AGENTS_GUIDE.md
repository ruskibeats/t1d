# Agent Definitions and Usage Guide

## Overview

This directory contains agent definitions for the T1D Companion multi-agent system. These definitions are used by development tools (Claude Code, Pi) to understand and interact with the agent architecture.

## Agent Types

### 1. Coordinator Agent

**Purpose**: Orchestrates all other agents and manages workflow

**Responsibilities**:
- Task delegation and routing
- Pipeline execution (safety → data → pattern → conversation)
- Error handling and fallbacks
- Agent lifecycle management

**Key Methods**:
- `startup()` - Initialize all agents
- `shutdown()` - Graceful shutdown
- `delegate_task(task_type, data)` - Route to specific agent
- `process_chat_message(message, user_id)` - Full conversation pipeline

**Location**: `app/agents/coordinator.py` (Python implementation)

---

### 2. DataIngestionAgent

**Purpose**: Handle CGM and meal tracker data ingestion

**Responsibilities**:
- Fetch glucose readings from Dexcom/Nightscout
- Retrieve context events (meals, insulin, exercise)
- Provide structured context for conversations
- Manage data synchronization pipelines

**Key Methods**:
- `handle({"action": "get_context", "user_id": <id>})` - Returns glucose, events, patterns

**Integration Points**:
- DexcomService: OAuth and API calls
- NightscoutService: Alternative CGM source
- SyncService: Background synchronization

**Data Flow**:
```
CGM API → Service Layer → DataIngestionAgent → Context → LLM
```

---

### 3. PatternAgent

**Purpose**: Detect and analyze glucose patterns and correlations

**Responsibilities**:
- Post-meal spike detection
- Overnight hypoglycemia identification
- Exercise effect analysis
- Nutritional impact correlation
- Time-in-range calculations

**Key Methods**:
- `handle({"action": "analyze_for_conversation", ...})` - Returns patterns, trends, correlations

**Integration Points**:
- PatternService: Statistical analysis
- Database: Glucose readings and events

**Analysis Types**:
- Time-in-Range: % within 70-180 mg/dL
- Spike Detection: >180 mg/dL post-meal
- Hypoglycemia: <70 mg/dL (especially overnight)
- Trend Analysis: Directional patterns over time

---

### 4. ConversationAgent

**Purpose**: Natural language conversation and LLM integration

**Responsibilities**:
- Context-aware response generation
- Pattern summarization in plain language
- Multi-turn conversation management
- RAG (Retrieval-Augmented Generation)

**Key Methods**:
- `handle({"message": "...", "context": {...}, "patterns": {...}})` - Returns response, confidence, sources

**Integration Points**:
- LLMService: OpenAI/Anthropic/OpenRouter integration
- Conversation history management
- RAG context retrieval

**RAG Context**:
```python
{
    "recent_glucose": [...],      # Last 20 readings
    "recent_events": [...],        # Last 10 events
    "pattern_summary": {...},      # Statistical patterns
    "user_profile": {...}          # User preferences
}
```

**Safety Features**:
- Emergency keyword detection
- Content filtering
- Escalation protocols

---

### 5. SafetyAgent

**Purpose**: Safety monitoring, content filtering, and escalation

**Responsibilities**:
- Emergency keyword detection
- Content safety validation
- Escalation to medical services
- Audit logging

**Key Methods**:
- `handle({"content": "...", "content_type": "..."})` - Returns is_safe, safety_level, reasons, requires_escalation

**Emergency Keywords**:
```python
[
    "emergency", "urgent", "help", "can't wake", "unconscious",
    "severe", "crisis", "911", "emergency room", "hospital",
    "kill myself", "suicide", "end it", "give up"
]
```

**Safety Levels**:
- `safe`: Content passed all checks
- `emergency`: Immediate escalation required

**Disclaimers Enforced**:
- "Educational insights, not medical advice"
- "Consult your healthcare provider"
- "Patterns indicate, not prescribe"

---

### 6. SummaryAgent

**Purpose**: Generate summaries and clinic-ready reports

**Responsibilities**:
- Pattern summaries (time-based)
- Clinic report generation
- Export formatting
- Trend documentation

**Key Methods**:
- `handle({"format": "text", "time_range": {...}})` - Returns summary in specified format

**Output Formats**:
- `text`: Plain language summaries
- `structured`: JSON for programmatic use
- `clinic`: Formatted for healthcare providers

---

## BaseAgent Class

All agents inherit from `BaseAgent`:

```python
class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"agents.{name}")
    
    async def handle(self, data: dict) -> dict:
        """Handle a task."""
        raise NotImplementedError(f"{self.name} must implement handle()")
    
    async def shutdown(self) -> None:
        """Shutdown agent resources."""
        pass
```

---

## Usage Examples

### Direct Task Delegation

```python
from app.agents.coordinator import AgentCoordinator

coordinator = AgentCoordinator()
await coordinator.startup()

# Delegate to specific agent
result = await coordinator.delegate_task(
    task_type="pattern",
    data={
        "action": "analyze_for_conversation",
        "user_id": user_id,
        "context": context
    }
)

await coordinator.shutdown()
```

### Full Conversation Pipeline

```python
# Process user message through full pipeline
response = await coordinator.process_chat_message(
    message="Why did I spike after dinner?",
    user_id=42,
    conversation_id=123
)

# Response includes:
# - Generated text
# - Safety check results
# - Pattern analysis
# - Metadata
```

### Pi Development Environment

```bash
# List available agents
pi subagent list

# Run specific agent task
pi subagent single \
  --agent coordinator \
  --task "Review conversation handling code"

# Chain multiple agents
pi subagent chain \
  --config workflow.json

# Parallel execution
pi subagent parallel \
  --agents "review,test,document" \
  --task "Implement feature"
```

---

## Agent Communication

### Pipeline Flow

```
User Message
    │
    ▼
SafetyAgent.handle()
    ├─ Check emergency keywords
    ├─ Validate content
    └─ Escalate if needed
    │
    ▼ (if safe)
DataIngestionAgent.handle()
    ├─ Fetch glucose readings
    ├─ Get recent events
    └─ Compile user profile
    │
    ▼
PatternAgent.handle()
    ├─ Analyze correlations
    ├─ Detect anomalies
    └─ Generate insights
    │
    ▼
ConversationAgent.handle()
    ├─ Build RAG context
    ├─ Call LLM
    └─ Generate response
    │
    ▼
Response to User
```

### Error Handling

```python
try:
    result = await coordinator.delegate_task("pattern", data)
except ValueError as e:
    # Unknown task type
    logger.error(f"Invalid task: {e}")
except RuntimeError as e:
    # Coordinator not running
    logger.error(f"Coordinator error: {e}")
```

---

## Development with Agents

### Adding a New Agent

1. **Create agent class** in `app/agents/`:

```python
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__("my_agent")
    
    async def handle(self, data: dict) -> dict:
        action = data.get("action")
        if action == "my_action":
            return await self._handle_action(data)
        return {"status": "ok"}
```

2. **Register in Coordinator**:

```python
# In AgentCoordinator.__init__()
self.agents["my_agent"] = MyAgent()

# In delegate_task()
agent_map["my_task"] = self.agents["my_agent"]
```

3. **Add tests** in `tests/unit/test_agents.py`

4. **Update documentation** in `AGENTS.md`

### Testing Agents

```python
@pytest.mark.asyncio
async def test_my_agent():
    agent = MyAgent()
    
    result = await agent.handle({
        "action": "my_action",
        "data": "test"
    })
    
    assert result["status"] == "ok"
```

---

## Production vs Development

### Production (Python Agents)

- In-process coordinator
- FastAPI integration
- Database persistence
- Real-time processing
- Full error handling

### Development (Pi Subagents)

- Separate processes
- Markdown/YAML definitions
- Ephemeral sessions
- AI-assisted development
- Documentation generation

---

## Best Practices

### For Agent Implementation

1. **Inherit from BaseAgent**: Get logging and structure
2. **Implement handle()**: Single entry point
3. **Use action pattern**: Check `data.get("action")`
4. **Return dictionaries**: Consistent response format
5. **Add error handling**: Catch and log exceptions
6. **Write tests**: Cover all action types
7. **Document methods**: Explain parameters and returns

### For Agent Usage

1. **Start coordinator first**: Call `startup()` before use
2. **Shutdown properly**: Call `shutdown()` on exit
3. **Handle errors**: Wrap in try/except
4. **Validate input**: Check required fields
5. **Use delegation**: Prefer `delegate_task()` over direct agent access
6. **Monitor performance**: Log execution time

---

## Monitoring

### Logging

All agents use structured logging:

```python
self.logger.info("Processing task", extra={
    "agent": self.name,
    "action": action,
    "user_id": user_id
})
```

### Metrics

- Agent execution time
- Task success/failure rates
- Error types and frequencies
- Queue depths (if async)

---

## Troubleshooting

### Agent Not Found

```python
# Error: Unknown task type
# Fix: Check agent_map in delegate_task()
agent_map = {
    "my_task": self.agents["my_agent"],  # Add mapping
}
```

### Coordinator Not Running

```python
# Error: "Agent coordinator is not running"
# Fix: Call startup() first
await coordinator.startup()
```

### Handle() Not Implemented

```python
# Error: "must implement handle()"
# Fix: Add handle() method
class MyAgent(BaseAgent):
    async def handle(self, data):
        return {"status": "ok"}
```

---

## References

- **Implementation**: `app/agents/coordinator.py`
- **System Docs**: `SYSTEM.md`
- **Agent Docs**: `AGENTS.md`
- **Development Guide**: `DEVELOPMENT.md`
- **Pi Subagents**: https://github.com/russell-taylor/pi-subagents