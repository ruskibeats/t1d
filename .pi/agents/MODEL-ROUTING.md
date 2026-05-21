# Subagent Model Routing — T1D Companion

## Simplified Strategy (2026-05-18 update)

**Use `openrouter/owl-alpha` for ALL subagent roles.**

Tested across 5+ full GRAPH task dispatches — works reliably for workers, scouts, and researchers.
No fallback models needed. On OpenRouter, always free.

| Agent | Model | Role |
|-------|-------|------|
| Worker | `openrouter/owl-alpha` | Implementation in forked async subagents |
| Scout | `openrouter/owl-alpha` | Read-only codebase scouting |
| Researcher | `openrouter/owl-alpha` | Audits, analysis, documentation |

## Key Rules

- **Always `async: true`**, `context: "fork"`, `cwd=/root/t1d`
- **Max 2-3 concurrent agents** — rate limits are PER-MODEL
- **NO `:high` thinking suffix** — use bare model names only
- **If 400**: try without `:free` suffix
- **If 429**: reduce concurrency, wait 10s
- **Track active run IDs** — ghost completions arrive 30-120s late

## Previously Tested Models (kept for reference)

| Model | Verdict |
|-------|---------|
| `openai/gpt-oss-120b:free` | Returns planning prose, no tool execution |
| `openai/gpt-oss-20b:free` | Returns planning prose, no tool execution |
| `nvidia/nemotron-nano-9b-v2:free` | Works but owl-alpha more reliable |
| `nvidia/nemotron-3-nano-30b-a3b:free` | Inconsistent tool execution |
| `qwen/qwen3-coder:free` | Inconsistent tool execution |
| `deepseek/deepseek-v4-flash:free` | Free tier discontinued, paid only |
| `nvidia/nemotron-3-super-120b-a12b:free` | Inconsistent tool execution |
| `poolside/laguna-xs.2:free` | Inconsistent tool execution |
| `poolside/laguna-m.1:free` | Returns planning output, no tool calls |
| `baidu/cobuddy:free` | Returns planning output, no tool calls |
| `inclusionai/ling-2.6-flash:free` | No longer free, paid only |
