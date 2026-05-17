# Subagent Model Routing — T1D Companion

## Core Strategy

- **Rate limits are PER-MODEL, not global.** 8+ agents on 8+ different models = no 429s.
- **Always use `async: true`** — never block the parent session.
- **Always use `context: "fork"`** — isolated child threads with parent history.
- **Always pass `cwd=/root/t1d`** — NOT inherited from parent.
- **Max 2-3 concurrent agents on the SAME model** — spread across models.
- **NO `:high` thinking suffix** — breaks many models. Use bare model names only.

## Top 5 Free Programming Models (Verified for Our Account)

| Rank | Model | Context | Tools | Structured | Notes |
|------|-------|---------|-------|------------|-------|
| 1 | `openai/gpt-oss-120b:free` | 131K | 🔧 | 📋 | Best for complex multi-file work |
| 2 | `openai/gpt-oss-20b:free` | 131K | 🔧 | 📋 | Fast, good for CRUD/hooks/schemas |
| 3 | `nvidia/nemotron-nano-9b-v2:free` | 128K | 🔧 | 📋 | Most reliable, balanced |
| 4 | `nvidia/nemotron-3-nano-30b-a3b:free` | 256K | 🔧 | 📋 | Large context, agentic |
| 5 | `qwen/qwen3-coder:free` | 1M | 🔧 | 📋 | Code-specialized, huge context |

## Next 5 Free Backup Models

| Rank | Model | Context | Tools | Notes |
|------|-------|---------|-------|-------|
| 6 | `deepseek/deepseek-v4-flash:free` | 1M | 🔧 | Huge context, fast |
| 7 | `nvidia/nemotron-3-super-120b-a12b:free` | 1M | 🔧📋 | Massive context |
| 8 | `poolside/laguna-xs.2:free` | 131K | 🔧 | Proven in previous runs |
| 9 | `poolside/laguna-m.1:free` | 131K | 🔧 | Proven in previous runs |
| 10 | `z-ai/glm-4.5-air:free` | 131K | 🔧📋 | Proven fixer model |

## Key Rules

1. **NO `:high` suffix** — use bare model names
2. **Always `async: true`**, `context: "fork"`, `cwd=/root/t1d`
3. **Workers: fork context. Reviewers: fresh context.**
4. **Max 2-3 concurrent on SAME model**
5. **If 400**: try without `:free` suffix; **If 429**: swap model
6. **Track active run IDs** for ghost completions (30-120s delay)
