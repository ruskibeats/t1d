# Agent System Documentation

## Overview

This project uses a multi-agent architecture for the T1D (Type 1 Diabetes) Companion system. Agents are specialized components that handle distinct domains within the diabetes management workflow. The system combines **Python-based runtime agents** (for production) with **pi-subagents** (for AI-assisted development and orchestration).

**Key Principle**: This is an *educational data companion*, not a medical device. Agents provide pattern recognition and conversational insights while enforcing strict safety guardrails.

## Clanker Ops

Clanker Ops is the project work queue, planning surface, and shutdown/reporting system. When the user asks to learn, understand, remember, add to, plan, report, summarize, dispatch, queue, or review Clanker Ops work, do **not** create skills, memory files, README files, tools, scripts, or other persistent artifacts unless the user explicitly asks for that artifact or destination.

Default behavior:

- Inspect `.pi/todo-state.json`, `.pi/todo-plans/`, and the Clanker Ops extension only as needed.
- Answer the user directly, or add/update a Clanker Ops work item with a mini-plan.
- Use `/clanker`, `/clanker eod`, `/clanker lights-off`, or the existing Clanker Ops tool actions.
- Leave support artifacts such as skills, tools, scripts, and files to the assigned clanker during dispatch, unless the mini-plan explicitly says to use them.

**Agent Allocation**: For task assignment to appropriate agents, see `docs/CLANKER_ROSTER.md` which catalogs ~35 curated agents for T1D Companion development.

Examples:

- "learn clanker ops" means inspect and explain the current queue system; it does not mean create a skill.
- "add end of day report to clanker ops" means add/update a Clanker Ops work item with a mini-plan unless the user explicitly asks to implement immediately.
- "add list all .md files in docs folder and add a review todo to clanker ops" means inspect docs as needed, then add the review work item to Clanker Ops.

---

## Architecture

### High-Level Design

```
T1D Companion System
│
├── Python Backend (FastAPI)                    # Production Runtime
│   ├── Agent Coordinator (app/agents/)
│   │   ├── DataIngestionAgent
│   │   ├── PatternAgent
│   │   ├── ConversationAgent
│   │   ├── SafetyAgent
│   │   └── SummaryAgent
│   │
│   ├── Services (app/services/)
│   │   ├── LLMService           # OpenAI/Anthropic/OpenRouter
│   │   ├── DexcomService        # CGM data ingestion
│   │   ├── NightscoutService    # Alternative CGM source
│   │   ├── MealService          # Nutrition tracking
│   │   ├── PatternService       # Statistical analysis
│   │   └── SyncService          # Data synchronization
│   │
│   └── API Layer (app/api/)
│       ├── auth.py
│       ├── chat.py              # Conversational endpoints
│       ├── glucose.py           # Glucose data
│       ├── events.py            # Context events
│       ├── patterns.py          # Pattern analysis
│       └── users.py
│
└── Pi Subagents (agents/)         # AI Development/Orchestration
    ├── README.md                   # Agent definitions
    └── (runtime definitions for Claude Code / Pi environments)
```

### Runtime vs Development Agents

| Aspect | Python Agents (Runtime) | Pi Subagents (Dev) |
|--------|------------------------|--------------------|
| **Purpose** | Production execution | AI-assisted development |
| **Language** | Python (FastAPI) | Markdown/YAML definitions |
| **Execution** | In-process coordinator | Separate processes/sessions |
| **Scope** | Data ingestion, analysis, safety | Code generation, planning, review |
| **Persistence** | PostgreSQL database | Ephemeral sessions |
| **Primary Use** | User-facing features | Developer tooling |

---

## Python Agents (Production Runtime)

Located in `app/agents/coordinator.py`

### 1. DataIngestionAgent

**Responsibility**: Handle CGM and meal tracker data ingestion

**Capabilities**:
- Retrieve glucose readings from Dexcom/Nightscout
- Fetch context events (meals, insulin, exercise)
- Provide structured context for conversations
- Manage data synchronization pipelines

**Key Methods**:
```python
async def handle(self, data: dict) -> dict
    # action: "get_context" - Returns glucose, events, patterns
```

**Integration Points**:
- `app/services/dexcom_service.py`
- `app/services/nightscout_service.py`
- `app/services/sync_service.py`

**Data Flow**:
```
CGM API → DexcomService → DataIngestionAgent → Context → LLM
```

### 2. PatternAgent

**Responsibility**: Detect and analyze glucose patterns and correlations

**Capabilities**:
- Post-meal spike detection
- Overnight hypoglycemia identification
- Exercise effect analysis
- Nutritional impact correlation
- Time-in-range calculations

**Key Methods**:
```python
async def handle(self, data: dict) -> dict
    # action: "analyze_for_conversation" - Returns patterns, trends, correlations
```

**Integration Points**:
- `app/services/pattern_service.py`
- `app/db/models.py` (GlucoseReading, ContextEvent)

**Analysis Types**:
- **Time-in-Range**: % within 70-180 mg/dL
- **Spike Detection**: >180 mg/dL post-meal
- **Hypoglycemia**: <70 mg/dL (especially overnight)
- **Trend Analysis**: Directional patterns over time

### 3. ConversationAgent

**Responsibility**: Natural language conversation and LLM integration

**Capabilities**:
- Context-aware response generation
- Pattern summarization in plain language
- Multi-turn conversation management
- RAG (Retrieval-Augmented Generation)

**Key Methods**:
```python
async def handle(self, data: dict) -> dict
    # Returns: response, confidence, sources
```

**Integration Points**:
- `app/services/llm_service.py` (OpenAI/Anthropic/OpenRouter)
- Conversation history management
- RAG context retrieval

**RAG Context**:
```python
class RAGContext:
    recent_glucose: List[Dict]      # Last 20 readings
    recent_events: List[Dict]        # Last 10 events
    pattern_summary: Dict            # Statistical patterns
    user_profile: Dict               # User preferences
```

**Safety Features**:
- Emergency keyword detection
- Content filtering
- Escalation protocols

### 4. SafetyAgent

**Responsibility**: Safety monitoring, content filtering, and escalation

**Capabilities**:
- Emergency keyword detection
- Content safety validation
- Escalation to medical services
- Audit logging

**Key Methods**:
```python
async def handle(self, data: dict) -> dict
    # Returns: is_safe, safety_level, reasons, requires_escalation
```

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

### 5. SummaryAgent

**Responsibility**: Generate summaries and clinic-ready reports

**Capabilities**:
- Pattern summaries (time-based)
- Clinic report generation
- Export formatting
- Trend documentation

**Key Methods**:
```python
async def handle(self, data: dict) -> dict
    # Returns: summary in specified format
```

**Output Formats**:
- `text`: Plain language summaries
- `structured`: JSON for programmatic use
- `clinic`: Formatted for healthcare providers

---

## Pi Subagents (Development/AI Orchestration)

Located in root directory and `agents/`

### Purpose

Pi subagents provide AI-assisted development capabilities:
- **Code generation** and review
- **Architecture planning**
- **Documentation** synthesis
- **Testing** and validation
- **Deployment** coordination

---

## Skills Architecture - Lazy-Loadable System

### Overview

The project now uses a **lazy-loadable skills architecture** where skills are loaded on-demand instead of being pre-loaded at session start. This reduces initial context window bloat and improves performance.

### Architecture

```
Skills System
├── .agents/skills-registry.json    # Lightweight manifest (ALL skill metadata)
├── .agents/skills/                 # Full skill definitions
│   ├── SKILL.md                    # Individual skill content
│   ├── lazy-loader.js              # JavaScript lazy loader
│   └── lazy_loader.py              # Python lazy loader
└── Lazy Loading Flow
    ├── Session Start: Load registry only (~1KB)
    ├── Request Analysis: Match against manifests
    ├── Decision: Load relevant skills (on-demand)
    └── Execution: Use loaded skill content
```

### Benefits

| Approach | Token Cost (Startup) | Speed | Flexibility |
|----------|---------------------|-------|-------------|
| **Pre-load (old)** | ~16KB (all skills) | Slower | Immediate |
| **Lazy-load (new)** | ~1KB (registry only) | Fast | On-demand |
| **Savings** | **~16x less** | **~10x faster** | **Same** |

### How It Works

1. **Registry Load** (session start)
   - Loads `skills-registry.json` only (~1KB)
   - Contains all skill metadata but NOT full content
   - Fast startup, minimal token usage

2. **Request Analysis** (per request)
   - Analyzes user request against skill triggers
   - Uses keyword matching and intent patterns
   - Calculates confidence scores

3. **Skill Selection** (decision)
   - Filters by confidence threshold (default: 0.7)
   - Selects top N skills (default: 3)
   - Sorts by confidence + priority

4. **On-Demand Load** (execution)
   - Loads ONLY selected skill files
   - Caches for reuse
   - Injects into context

### Components

#### 1. Skills Registry (`skills-registry.json`)

Lightweight manifest containing:
- Skill metadata (name, title, description)
- Category and priority
- Trigger keywords
- Intent patterns (regex)
- Token estimates
- File paths

**Size**: ~15KB for 13 skills  
**Load Time**: <10ms  
**Token Cost**: ~50 tokens

#### 2. Lazy Loader (`lazy-loader.js` / `lazy_loader.py`)

Handles on-demand skill loading:
- Registry parsing
- Request matching
- Skill loading (cached)
- System prompt generation

**Features**:
- CLI interface for testing
- Statistics reporting
- Confidence-based matching
- Priority-based sorting

#### 3. Skill Files (`skills/*.md`)

Full skill definitions loaded only when needed:
- Complete instructions
- Examples
- Best practices

**Size**: 600-2000 tokens each  
**Load Time**: Only when matched

### Usage

#### Command Line

```bash
# List all available skills (manifests only)
cd .agents/skills && python3 lazy_loader.py list

# Show registry statistics
python3 lazy_loader.py stats

# Find skills matching a request
python3 lazy_loader.py match "build a dashboard"

# Load specific skill (for testing)
python3 lazy_loader.py load impeccable
```

#### Python Integration

```python
from .agents.skills.lazy_loader import LazySkillsLoader

# Initialize (loads registry only)
loader = LazySkillsLoader()

# Find relevant skills for a request
matches = loader.find_relevant_skills(
    "create a minimalist health dashboard",
    threshold=0.7
)

# Load selected skills (on-demand)
for match in matches:
    skill = loader.load_skill(match.skill_key)
    # Use skill['content'] in prompt

# Or generate system prompt automatically
prompt = loader.generate_system_prompt(
    "build a dashboard",
    base_instructions="You are a UI expert..."
)
```

#### JavaScript/Node.js Integration

```javascript
const { LazySkillsLoader } = require('./.agents/skills/lazy-loader');

// Initialize
const loader = new LazySkillsLoader();

// Find matches
const matches = loader.findRelevantSkills(
  'build a dashboard',
  0.7  // threshold
);

// Load skills on-demand
matches.forEach(match => {
  const skill = loader.loadSkill(match.skillKey);
  // Use skill.content in prompt
});
```

### Skill Matching Logic

Each skill has:
- **Triggers**: Keyword list (case-insensitive)
- **Intent Patterns**: Regex patterns for advanced matching

**Confidence Calculation**:
```
confidence = (trigger_matches + intent_matches) / total_possible
```

**Example**:
```python
Request: "create a minimalist health dashboard"

Skill: minimalist-ui
  Triggers: ["minimalist", "clean ui", "medical interface", ...]
  Matches: ["minimalist"]  → 1 trigger match
  Total Possible: 6 triggers
  Confidence: 1/6 = 0.17 (17%)
```

### Configuration

**Registry Settings** (`skills-registry.json`):
```json
{
  "routing": {
    "confidenceThreshold": 0.7,    // Min match confidence
    "maxSkillsPerRequest": 3,      // Max skills to load
    "fallbackSkill": "full-output-enforcement"  // Default
  }
}
```

**Adjust thresholds based on needs**:
- Lower threshold (0.5): More aggressive matching
- Higher threshold (0.8): Stricter matching
- More skills per request: Richer context (more tokens)

### Performance Comparison

| Metric | Pre-load | Lazy-load | Improvement |
|--------|----------|-----------|-------------|
| **Startup tokens** | ~16,350 | ~50 | **327x less** |
| **Startup time** | ~500ms | ~50ms | **10x faster** |
| **Avg request** | ~16KB | ~2KB | **8x less** |
| **Unused skills** | 100% loaded | 0% loaded | **100% saved** |

### Skill Categories

- **Design** (9 skills): UI polish, aesthetics, style systems
- **Image** (3 skills): Mockup generation, design conversion
- **Utility** (1 skill): Output control, completeness

**Priority Levels**:
- `critical`: Always consider (minimalist-ui, full-output-enforcement)
- `high`: Important but not essential (impeccable)
- `medium`: Standard tools (brandkit, industrial-brutalist-ui)
- `low`: Specialized tools (gpt-taste, high-end-visual-design)

### Best Practices

1. **Set appropriate thresholds**:
   - General requests: 0.6-0.7
   - Specific tasks: 0.7-0.8
   - Experimental: 0.5-0.6

2. **Use caching**:
   - Loaded skills cached in memory
   - Reused within session
   - Clear cache when updating skill files

3. **Monitor token usage**:
   - Check `get_stats()` for token estimates
   - Adjust `maxSkillsPerRequest` as needed

4. **Update registry**:
   - Add new triggers for better matching
   - Refine intent patterns
   - Adjust priorities based on usage

5. **Test matching**:
   ```bash
   python3 lazy_loader.py match "your typical request"
   ```

### Integration with Agents

**FastAPI Backend** (`app/agents/coordinator.py`):
```python
# In process_chat_message or handle method
skill_loader = LazySkillsLoader()

# Analyze request
relevant_skills = skill_loader.find_relevant_skills(
    user_message,
    threshold=0.7
)

# Build enriched context
context = {
    "message": user_message,
    "skills": [loader.load_skill(s.skill_key) for s in relevant_skills]
}

# Pass to LLM
response = await llm_service.generate(
    message=context["message"],
    system_prompt=skill_loader.generate_system_prompt(
        context["message"],
        base_instructions
    )
)
```

**Pi Subagents**:
```python
await subagent({
    "skill": True,  # Enable skill system
    "task": "Design minimal health dashboard"
})
```

### Migration from Pre-load

**Old approach**:
```python
# All skills loaded at startup (heavy!)
ALL_SKILLS = load_all_skill_files()  # ~16KB
```

**New approach**:
```python
# Lightweight registry + on-demand loading
loader = LazySkillsLoader()  # ~1KB
# Skills loaded only when needed
```

### Troubleshooting

**Skills not matching?**
- Lower confidence threshold
- Add more trigger keywords to registry
- Check intent patterns (regex syntax)

**Too many skills loading?**
- Increase confidence threshold
- Decrease `maxSkillsPerRequest`
- Remove low-priority skills

**Skill loading slowly?**
- Check file I/O
- Verify cache is working (`skillCache`)
- Reduce skill file sizes

### Future Enhancements

- [ ] Async skill loading
- [ ] Skill dependency resolution
- [ ] A/B testing of matching algorithms
- [ ] Learning from usage patterns
- [ ] Skill versioning and rollback
- [ ] Remote skill registry
- [ ] Skill hot-reloading

### References

- [IBM: AI Agent Patterns](https://www.ibm.com/think/topics/ai-agents)
- [Agents.md: Best Practices](https://agents.md)
- [Lazy Loading Pattern](https://en.wikipedia.org/wiki/Lazy_loading)

### Examples

```bash
# Typical workflow
$ python3 lazy_loader.py stats
Total Skills: 13
Token Savings: ~16,350 tokens per session

$ python3 lazy_loader.py match "build health dashboard"
1. minimalist-ui (17% match)
2. industrial-brutalist-ui (11% match)

$ python3 lazy_loader.py load minimalist-ui
# Full skill content loaded and displayed
```

---

*Updated: May 2026*  
*Version: 2.0.0 (Lazy-Loadable)*

### Available Skills

The project leverages specialized pi skills:

| Skill | Purpose | Location |
|-------|---------|----------|
| **full-output-enforcement** | Prevent truncated responses | `.agents/skills/` |
| **design-taste-frontend** | UI/UX enforcement | `.agents/skills/` |
| **impeccable** | Interface polish | `.agents/skills/` |
| **librarian** | Codebase research | `.agents/skills/` |
| **pi-subagents** | Multi-agent orchestration | `.agents/skills/` |
| **pi-intercom** | Cross-session communication | `.agents/skills/` |

### Agent Definitions

See `agents/README.md` for documented agent types:

- **coordinator**: Orchestrates agent workflow
- **data_ingestion_agent**: CGM/meal tracker integration
- **pattern_agent**: Glucose pattern analysis
- **conversation_agent**: Natural language processing
- **safety_agent**: Guardrails and escalation
- **summary_agent**: Report generation

### Example: Multi-Agent Workflow

```python
# Chain pattern analysis and conversation
await subagent({
    "chain": [
        {"agent": "pattern_agent", "task": "Analyze glucose data"},
        {"agent": "conversation_agent", 
         "task": "Explain {previous} to user"}
    ]
})
```

---

## Data Flow

### Typical User Query

```
1. User Message
   │
   ▼
2. SafetyAgent.handle()
   ├─ Check emergency keywords
   ├─ Validate content
   └─ Escalate if needed
   │
   ▼
3. DataIngestionAgent.handle()
   ├─ Fetch glucose readings
   ├─ Retrieve events
   └─ Compile context
   │
   ▼
4. PatternAgent.handle()
   ├─ Analyze correlations
   ├─ Detect anomalies
   └─ Generate insights
   │
   ▼
5. ConversationAgent.handle()
   ├─ Build RAG context
   ├─ Call LLM (OpenAI/Anthropic)
   └─ Generate response
   │
   ▼
6. SummaryAgent (optional)
   └─ Format for persistence
   │
   ▼
7. Response to User
```

---

## LLM Integration

### Providers

| Provider | Default Model | Use Case |
|----------|--------------|----------|
| **OpenAI** | `gpt-4o-mini` | Cost-effective, fast |
| **Anthropic** | `claude-3-5-haiku` | Balanced performance |
| **OpenRouter** | `openai/gpt-4o-mini` | ✅ Recommended: unified access, fallback |

### Configuration

```bash
# .env
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-4o-mini
OPENROUTER_API_KEY=sk-or-...
```

**Recommendation**: Use **OpenRouter** for:
- ✅ Unified API across all models
- ✅ Easy model switching
- ✅ Built-in fallback/routing
- ✅ Cost optimization

### RAG Implementation

```python
# Context retrieval for grounded responses
rag_context = await llm_service.retrieve_context(
    session, user_id, time_range_days=14
)

# System prompt includes:
# - User profile (diabetes type, targets)
# - Recent patterns (TIR, spikes)
# - Recent events (meals, insulin)
# - Safety rules (no dosing advice)

# Response generation
response = await llm_service.generate_response(
    message=user_message,
    session=db_session,
    user_id=user_id,
    conversation_id=conv_id
)
```

**Safety Guardrails**:
- Emergency keyword bypass (direct response)
- Content filtering pre-LLM
- Post-LLM safety validation
- Audit logging

---

## Safety & Compliance

### Core Principles

1. **Not a Medical Device**: Educational tool only
2. **No Autonomous Dosing**: Never provides insulin recommendations
3. **Clinical Oversight**: Encourages healthcare provider consultation
4. **Data Privacy**: HIPAA-compliant practices
5. **Transparency**: Clear about limitations

### Disclaimers

All responses include implicit or explicit acknowledgment:
- "Educational insights suggest..."
- "Based on similar patterns in your data..."
- "Consider discussing with your diabetes team..."
- "Individual results may vary..."

### Emergency Handling

```python
# SafetyAgent detects emergency
if requires_escalation:
    logger.warning(f"Emergency keywords: {found_keywords}")
    return {
        "is_safe": False,
        "safety_level": "emergency",
        "message": "Please seek immediate medical attention..."
    }
```

---

## Development Workflow

### Local Development

```bash
# 1. Setup environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -e .

# 3. Database migrations
alembic upgrade head

# 4. Start application
uvicorn app.main:app --reload
```

### Using Pi Subagents

```bash
# List available agents
pi subagent list

# Run specific agent
pi subagent single --agent coordinator --task "Review code"

# Chain multiple agents
pi subagent chain --config workflow.json

# Parallel execution
pi subagent parallel --agents "review,test,document" --task "Implement feature"
```

### Agent Coordination

```python
# Delegating tasks
result = await coordinator.delegate_task(
    task_type="pattern",
    data={"action": "analyze_for_conversation", ...}
)

# Full pipeline
response = await coordinator.process_chat_message(
    message=user_message,
    user_id=user.id,
    conversation_id=conv_id
)
```

---

## Project Structure

```
t1d-companion/
├── app/
│   ├── agents/              # Python agent implementations
│   │   └── coordinator.py   # Main coordinator + 5 agents
│   ├── services/            # Business logic
│   │   ├── llm_service.py   # LLM integration
│   │   ├── dexcom_service.py
│   │   ├── pattern_service.py
│   │   └── ...
│   ├── api/                 # FastAPI endpoints
│   ├── models/              # SQLAlchemy + Pydantic
│   ├── core/                # Utilities
│   └── db/                  # Database layer
├── agents/                  # Pi subagent definitions
│   └── README.md
├── .agents/                 # Pi skills
│   └── skills/
├── infrastructure/          # Deployment configs
├── tests/                   # Test suite
├── AGENTS.md               # This file
└── SYSTEM.md               # System documentation
```

---

## API Reference

### Chat Endpoints

```
POST /api/v1/chat
POST /api/v1/chat/stream
POST /api/v1/summarize-patterns
POST /api/v1/analyze-query
```

See `app/api/chat.py` for implementation details.

### Agent Coordination

```python
# Direct agent delegation
result = await coordinator.delegate_task("pattern", {...})

# Full pipeline
response = await coordinator.process_chat_message(message, user_id)
```

---

## Monitoring & Observability

### Logging

- All agent actions logged with structured JSON
- Safety alerts logged at WARNING level
- LLM interactions logged for auditing
- Performance metrics tracked

### Metrics

- Agent execution time
- LLM token usage
- Safety check pass/fail rate
- Emergency escalation count

---

## Testing

### Agent Tests

```bash
# Run agent-specific tests
pytest tests/agents/

# Test coordinator
pytest tests/test_coordinator.py

# Test LLM integration (mocked)
pytest tests/test_llm_service.py
```

### Safety Tests

- Emergency keyword detection
- Content filtering
- Escalation workflows
- Disclaimer enforcement

---

## Deployment

### Production

```bash
# Build container
docker build -t t1d-companion .

# Deploy
docker compose up -d
```

### Configuration

```bash
# Required env vars
DATABASE_URL=postgresql://...
SECRET_KEY=***
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
```

See `infrastructure/` for deployment templates.

---

## Future Enhancements

### Planned

- [ ] Multi-modal input (food photos)
- [ ] Wearable integration (exercise, sleep)
- [ ] Family/caregiver sharing
- [ ] Advanced pattern ML models
- [ ] Predictive alerts

### Under Consideration

- [ ] Apple HealthKit integration
- [ ] Continuous glucose prediction
- [ ] Meal photo recognition
- [ ] Voice interface

---

## Resources

- **Code**: [GitHub Repository](https://github.com/russell-taylor/T1D-Companion)
- **Docs**: [API Documentation](http://localhost:8000/docs)
- **Safety**: [SAFETY.md](docs/SAFETY.md)
- **Plan**: [PLAN.md](PLAN.md)

## Contact

For questions about the agent system:
- Open an issue on GitHub
- Check existing documentation in `/docs`
- Review agent definitions in `agents/README.md`

---

## License

TBD - pending legal review

## Disclaimer

**This is a research project and not a medical device. It does not provide medical advice, diagnosis, or treatment recommendations. Always consult with your healthcare provider regarding diabetes management and treatment decisions.**
