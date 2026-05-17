# Free (& Cheap) OpenRouter Model Benchmark for Subagent Work

**Date:** 2026-05-17  
**Tests:** 5 agent-suitability tests × multiple models  
**Scoring:** 0-2 per test, max 10 points

---

## Executive Summary

**BREAKTHROUGH: poolside/laguna models score 10/10 — the first free models suitable as primary subagent workers.** Both `poolside/laguna-xs.2:free` and `poolside/laguna-m.1:free` achieve perfect scores across all 5 agent-suitability tests. They are now the recommended free models for subagent work. Other free models (nemotron-3-super, glm-4.5-air) remain usable only for review/scout roles (5-6/10). Multiple models are rate-limited (429) or reasoning-only, making them unsuitable or incompatible with pi's subagent system.

---

## Results Table

| Model | T1 Tool | T2 Pattern | T3 Multi | T4 Valid | T5 Focus | Total | Status | Rating |
|-------|---------|------------|----------|----------|----------|-------|--------|--------|
| **poolside/laguna-xs.2:free** | 2 | 2 | 2 | 2 | 2 | **10/10** | ✅ Works | ★★★ PRIMARY |
| **poolside/laguna-m.1:free** | 2 | 2 | 2 | 2 | 2 | **10/10** | ✅ Works | ★★★ PRIMARY |
| **nemotron-3-super-120b-a12b:free** | 2 | 0 | 0 | 2 | 2 | **6/10** | ✅ Works | ★ REVIEWER |
| **nemotron-nano-9b-v2:free** | 0 | 0 | 2 | 2 | 0 | **4/10** | ✅ Works | ★ REVIEWER |
| **glm-4.5-air:free** | 0 | 0 | 2 | 2 | 0 | **4/10** | ⚠️ Reasoning-only | ★ REVIEWER |
| **gpt-oss-120b:free** | 0 | 1 | 2 | 0 | 0 | **3/10** | ⚠️ Inconsistent | ✗ AVOID |
| **gpt-oss-20b:free** | 0 | 1 | 0 | 0 | 0 | **1/10** | ⚠️ Weak | ✗ AVOID |
| **minimax-m2.5:free** | 0 | 0 | 0 | 2 | 2 | **4/10** | ⚠️ Partial RL | ★ REVIEWER |
| **tencent/hy3-preview** | — | — | — | — | — | **N/A** | ⚠️ Reasoning-only | ✗ BROKEN |
| **deepseek-v4-flash:free** | 0 | 0 | 0 | 0 | 0 | **0/10** | ✗ Broken | ✗ BROKEN |
| **qwen3-coder:free** | — | — | — | — | — | **N/A** | ✗ Rate limited | ✗ UNREACHABLE |
| **qwen3-next-80b:free** | — | — | — | — | — | **N/A** | ✗ Rate limited | ✗ UNREACHABLE |
| **llama-3.3-70b:free** | — | — | — | — | — | **N/A** | ✗ Rate limited | ✗ UNREACHABLE |
| **hermes-3-405b:free** | — | — | — | — | — | **N/A** | ✗ Rate limited | ✗ UNREACHABLE |
| **gemma-4-26b:free** | — | — | — | — | — | **N/A** | ✗ Rate limited | ✗ UNREACHABLE |

### Rating Key
- **★★★ PRIMARY (9-10):** Reliable for implementation work — *poolside/laguna models qualified*
- **★★ BACKUP (7-8):** Good secondary worker — *none qualified*
- **★ REVIEWER (5-6):** Usable for review/scout roles only
- **✗ AVOID:** Broken, rate-limited, or too unreliable

---

## Test Descriptions

| Test | What it measures | Why it matters for subagents |
|------|-----------------|------------------------------|
| **T1: Tool Obedience** | Does the model output tool calls vs just describing actions? | A subagent that only describes code instead of writing it is useless |
| **T2: Pattern Copying** | Can it read existing code and replicate conventions? | Subagents must follow repo style (Pydantic v2, ConfigDict, etc.) |
| **T3: Multi-File** | Can it create multiple coordinated files? | Real features span models + schemas + routes |
| **T4: Validation Loop** | Does it run tests and fix failures? | Self-healing agents that verify their own work |
| **T5: Context Pressure** | Does it stay focused with 500+ char filler? | Subagents get large context windows; must not get distracted |

---

## Detailed Model Notes

### poolside/laguna-xs.2:free — ★★★ PRIMARY (10/10)
- **Health:** ✅ Responds correctly
- **T1:** Perfect — outputs `write` tool call format
- **T2:** Perfect — reads file, creates Pydantic v2 schemas matching style
- **T3:** Perfect — creates 3 coordinated files with proper structure
- **T4:** Perfect — creates code + tests, runs pytest, fixes until passing
- **T5:** Perfect — ignores 500+ char filler, creates needle file
- **Context:** 131k
- **Verdict:** **RECOMMENDED FREE MODEL for primary subagent work.** The only free model that passed all 5 tests. Fast response (~2s), good token efficiency (~200 avg). Strong tool-use formatting.
- **Provider:** Poolside

### poolside/laguna-m.1:free — ★★★ PRIMARY (10/10)
- **Health:** ✅ Responds correctly
- **T1:** Perfect — outputs `write` tool call format
- **T2:** Perfect — reads file, creates Pydantic v2 schemas matching style (2082 tokens for detailed code)
- **T3:** Perfect — creates 3 coordinated files
- **T4:** Perfect — creates code + tests, runs pytest, fixes until passing (2074 tokens)
- **T5:** Perfect — ignores 500+ char filler, creates needle file
- **Context:** 131k
- **Verdict:** **RECOMMENDED FREE MODEL for primary subagent work.** Identical performance to xs.2 but larger (more detailed output on T2/T4). Both models are now the best free options available.
- **Provider:** Poolside

### tencent/hy3-preview — ✗ BROKEN (reasoning-only)
- **Health:** ✅ Responds, but ALL output goes to `reasoning` field, not `content`
- **Verdict:** **Completely unusable as a subagent.** Pi reads `content`, not `reasoning`.
- **Provider:** Tencent

### z-ai/glm-4.5-air:free — 4/10 ★ (reasoning-only)
- **Health:** ⚠️ Reasoning-only for ping
- **Verdict:** Inconsistent — sometimes outputs content, sometimes reasoning-only.
- **Provider:** Z-AI

### nvidia/nemotron-3-super-120b-a12b:free — 6/10 ★ BEST FREE (before poolside)
- **Strengths:** Passed T1, T4, T5. 1M context.
- **Weaknesses:** Failed T2, T3 (hit token limit). Slow.
- **Verdict:** Usable as reviewer/scout.
- **Provider:** NVIDIA

### nvidia/nemotron-nano-9b-v2:free — 4/10 ★
- **Verdict:** Good for simple code generation. 9B size is efficient.
- **Provider:** NVIDIA

### openai/gpt-oss-120b:free — 3/10 ✗
- **Verdict:** Inconsistent. Sometimes outputs good content, sometimes empty.
- **Provider:** OpenAI

### deepseek/deepseek-v4-flash:free — 0/10 ✗ BROKEN
- **Issue:** Returns `null` content with garbled reasoning text.
- **Provider:** DeepSeek

### Rate-Limited Models (all 429)
- qwen/qwen3-coder:free, qwen/qwen3-next-80b-a3b-instruct:free, meta-llama/llama-3.3-70b-instruct:free, nousresearch/hermes-3-llama-3.1-405b:free, google/gemma-4-26b-a4b-it:free
- All need BYOK for access.

---

## Critical Findings

1. **Reasoning-Only Models Are Dealbreakers** — `tencent/hy3-preview`, `z-ai/glm-4.5-air:free` put responses in `reasoning` field, which pi ignores.

2. **Rate Limits Block 42% of Free Models** — Venice provider is particularly restrictive.

3. **Poolside Models Are Now Recommended** — First free models to pass all 5 tests (10/10).

---

## Recommendations

### Suggested Subagent Model Roster

| Role | Primary | Backup | Free Fallback |
|------|---------|--------|---------------|
| **worker** | gpt-4o-mini | claude-3-5-haiku | poolside/laguna-xs.2:free |
| **reviewer** | claude-3-5-haiku | gpt-4o-mini | nemotron-3-super-120b:free |
| **scout** | gpt-4o-mini | claude-3-5-haiku | nemotron-nano-9b-v2:free |

### Models to Avoid
- **tencent/hy3-preview** — Reasoning-only
- **deepseek/deepseek-v4-flash:free** — Broken
- **All Venice provider free models** — Rate limited without BYOK

---

## Raw Data

`.agents/benchmark_results.json` | `.agents/poolside_results.json` | `.agents/run_subagent_benchmark.py`