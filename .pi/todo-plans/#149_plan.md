# Plan: [ARCH-BACKEND] Sprint 14: Agent Pipeline Deepening

## Intended Outcome
Refactor the Agent pipeline to improve **locality** and **leverage**:
1. Extract **Safety Scaffold** as a shared module (deduplicate from SafetyAgent and LLMService)
2. Make each agent receive dependencies via constructor injection
3. Create a **Pattern Analysis** interface with confidence scoring

## Step-by-Step

### Phase 1: Safety Scaffold Extraction (S14-A1)
1. Create `app/ai/safety_scaffold.py` with shared validation logic
2. Move policy violation patterns from SafetyAgent to SafetyScaffold
3. Update SafetyAgent to delegate to SafetyScaffold
4. Update LLMService.generate_response to use SafetyScaffold
5. Add tests for shared safety logic in `tests/test_safety_scaffold.py`

### Phase 2: Agent Dependency Injection (S14-A2)
1. Modify BaseAgent to accept dependencies via constructor
2. Update PatternAgent to receive PatternService instance
3. Update DataIngestionAgent to receive LLMService instance
4. Update ConversationAgent to receive LLMService instance
5. Add tests verifying dependencies can be mocked

### Phase 3: Pattern Analysis Interface (S14-A3)
1. Create `app/metrics/pattern_interface.py` with PatternAnalyzer protocol
2. Implement ConcreteAnalyzers for each pattern type
3. Create PatternOrchestrator to run all detectors
4. Update LLMService to use PatternOrchestrator
5. Add tests in `tests/test_pattern_interface.py`

## Files
- `app/agents/coordinator.py` - Agent classes
- `app/ai/safety.py` - SafetyScaffold (new)
- `app/services/pattern_service.py` - Pattern interface (new)
- `app/services/llm_service.py` - Updated safety usage

## Verification
```bash
pytest tests/test_safety_scaffold.py -v
pytest tests/test_agent_injection.py -v
pytest tests/test_pattern_interface.py -v
python -c "from app.agents.coordinator import AgentCoordinator; print('OK')"
```

## Skills Required
- `improve-codebase-architecture` - Deepening modules for testability
- `tdd` - Test-first approach for new interfaces
- Tests should pass: `pytest tests/test_safety_*.py tests/test_pattern_*.py`

## Audit
### Files Changed
- `app/ai/safety_scaffold.py` (new)
- `app/agents/coordinator.py` (modified)
- `app/services/pattern_interface.py` (new)
- `tests/test_safety_scaffold.py` (new)
- `tests/test_pattern_interface.py` (new)

### Verification Results
(Populate after implementation)

### Token Burn Estimate
~15,000 tokens (safety extraction), ~12,000 tokens (DI), ~18,000 tokens (pattern interface)

### Blockers/Follow-ups
None identified at planning stage.