# LLM Configuration Guide - T1D Companion

## Overview
The T1D Companion uses a unified LLM service layer supporting multiple providers:
- **OpenAI** - GPT-4o-mini, GPT-4
- **Anthropic** - Claude 3.5 Haiku, Claude 3 Opus
- **OpenRouter** - Unified access to 100+ models

## Configuration

### Environment Variables (`.env`)

```bash
# Primary LLM Provider
# Options: openai, anthropic, openrouter
LLM_PROVIDER=openrouter

# Specific model (optional, uses provider default if not set)
LLM_MODEL=openai/gpt-4o-mini

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...

# OpenRouter settings (optional)
OPENROUTER_REFERER=T1D-Companion
```

### Model Names by Provider

| Provider | Model Format | Examples |
|----------|-------------|----------|
| **OpenAI** | `gpt-4o-mini` | gpt-4o-mini, gpt-4o, gpt-4-turbo |
| **Anthropic** | `claude-3-5-haiku-20241022` | claude-3-5-haiku, claude-3-5-sonnet, claude-3-opus |
| **OpenRouter** | `openai/gpt-4o-mini` | openai/gpt-4o-mini, anthropic/claude-3.5-haiku, google/gemini-1.5-flash |

## Usage

### Default Configuration (Recommended)

The default configuration uses **OpenRouter** with `openai/gpt-4o-mini`:

```python
from app.services.llm_service import LLMService

# Uses config.llm_provider and config.llm_model
service = LLMService()  
```

### Explicit Provider Selection

```python
from app.services.llm_service import LLMProvider

# OpenAI GPT-4o
service = LLMService(provider=LLMProvider.OPENAI)

# Anthropic Claude 3.5
service = LLMService(provider=LLMProvider.ANTHROPIC, model="claude-3-5-haiku-20241022")

# OpenRouter with any model
service = LLMService(provider=LLMProvider.OPENROUTER, model="anthropic/claude-3.5-sonnet")
```

### API Integration

All chat endpoints automatically use the configured LLM:

```bash
# Uses configured provider/model
POST /api/v1/chat
POST /api/v1/chat/stream
POST /api/v1/summarize-patterns
POST /api/v1/analyze-query
```

## Provider Comparison

| Feature | OpenAI | Anthropic | OpenRouter |
|---------|--------|-----------|------------|
| **Best Model** | GPT-4o | Claude 3.5 | All |
| **Pricing** | Low | Medium | Varies |
| **Context** | 128K | 200K | Depends |
| **Unified API** | ❌ | ❌ | ✅ |
| **Fallback** | N/A | N/A | ✅ |
| **Recommended** | ✅ | ✅ | ⭐ |

### Recommendation

**Use OpenRouter** for:
- ✅ Unified API across all models
- ✅ Easy model switching
- ✅ Built-in fallback/routing
- ✅ Single billing dashboard
- ✅ Best overall flexibility

## Fallback Strategy

If primary LLM fails, the system gracefully falls back:

1. **LLM Service Error** → Pattern-based response
2. **API Timeout** → Cached/last response
3. **No API Key** → Pattern summaries only

```python
try:
    response = await llm_service.generate_response(...)
except LLMServiceError:
    # Falls back to pattern-based analysis
    response = generate_fallback_response()
```

## Security & Privacy

- All API keys stored in environment variables
- No user data sent to LLMs without consent
- HIPAA-compliant request patterns
- Audit logging for all LLM interactions
- Emergency keywords bypass LLM (direct response)

## Cost Optimization

| Strategy | Savings |
|----------|---------|
| Use GPT-4o-mini vs GPT-4 | 90%+ |
| Cache frequent queries | 30-50% |
| Batch non-urgent requests | 20% |
| OpenRouter intelligent routing | 15% |

## Troubleshooting

### LLM Not Responding
```bash
# Check API key
export OPENROUTER_API_KEY=sk-...

# Verify configuration
python3 -c "from app.config import get_settings; print(get_settings().llm_provider)"
```

### High Latency
```bash
# Switch to faster model
LLM_MODEL=openai/gpt-4o-mini
# Or use local/cheaper provider
LLM_PROVIDER=openai
```

### Cost Spikes
```bash
# Enable request logging
export LLM_LOG_REQUESTS=true

# Limit context size
# (Configured in app/services/llm_service.py)
```

## Examples

### Basic Chat
```python
from app.services.llm_service import get_llm_service

llm = get_llm_service()
response = await llm.generate_response(
    message="Why did I spike after dinner?",
    session=session,
    user_id=user.id
)
print(response["response"])
```

### Pattern Summary
```python
summary = await llm.summarize_patterns(pattern_data, user.id)
# "Your time in range is 78% this week..."
```

### Custom Provider
```python
service = LLMService(
    provider=LLMProvider.OPENROUTER,
    model="anthropic/claude-3.5-sonnet",
    api_key="your-key"
)
```

## Performance

| Metric | Typical |
|--------|---------|
| Response time (GPT-4o-mini) | 500-1000ms |
| Response time (Claude 3.5) | 800-2000ms |
| Tokens per response | 200-500 |
| Cost per query | $0.0001-0.001 |

## Resources

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [OpenAI API Reference](https://platform.openai.com/docs)
- [Anthropic API Reference](https://docs.anthropic.com)
- [T1D Companion GitHub](https://github.com/ruskibeats/t1d)
