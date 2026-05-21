# Plan: [ARCH-LLM] Sprint 18: LLM Provider Abstraction Layer

## Intended Outcome
Create an **LLM Provider** interface layer for better flexibility and testing:
1. Create Provider protocol with generate_response method
2. Implement concrete adapters for OpenAI, Anthropic, OpenRouter, MiniMax
3. Create ProviderChain for fallback logic
4. Update LLMService to use the new architecture

## Step-by-Step

### Phase 1: Provider Protocol (S18-L1)
1. Create `app/services/llm/provider.py` with Provider protocol
2. Define `ProviderResponse` and `ProviderError` types
3. Move common logic (timeout, error handling) to shared utilities
4. Write tests in `tests/test_llm_provider.py`

### Phase 2: Concrete Adapters (S18-L2)
1. Implement OpenAIAdapter with `_call_openai` logic
2. Implement AnthropicAdapter with `_call_anthropic` logic
3. Implement OpenRouterAdapter with unified access logic
4. Implement MiniMaxAdapter for free-tier model
5. Tests in `tests/test_llm_adapters.py`

### Phase 3: Provider Chain (S18-L3)
1. Create `ProviderChain` in `app/services/llm/chain.py`
2. Implement configurable fallback ordering
3. Add health check method for each provider
4. Update LLMService to use ProviderChain
5. Add tests in `tests/test_provider_chain.py`

## Files
- `app/services/llm_service.py` - Refactor
- `app/services/llm/provider.py` (new)
- `app/services/llm/adapters/*.py` (new directory)
- `app/services/llm/chain.py` (new)
- `tests/test_llm_*.py` (new)

## Verification
```bash
pytest tests/test_llm_provider.py -v
pytest tests/test_llm_adapters.py -v
pytest tests/test_provider_chain.py -v
# Manual: test with various provider configurations
OPENROUTER_API_KEY=xxx pytest tests/ -k "llm" -v
```

## Skills Required
- `improve-codebase-architecture` - Interface extraction
- `tdd` - Adapter testing with mock HTTP

## Audit
### Files Changed
- `app/services/llm_service.py` (modified)
- `app/services/llm/provider.py` (new)
- `app/services/llm/adapters/*.py` (new)
- `app/services/llm/chain.py` (new)
- `tests/test_llm_*.py` (new)

### Token Burn Estimate
~15,000 tokens (protocol), ~20,000 tokens (adapters), ~12,000 tokens (chain)

### Blockers/Follow-ups
Provider API keys needed for integration testing.