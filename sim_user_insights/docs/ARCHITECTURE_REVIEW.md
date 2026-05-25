# Architecture Review — T1D Companion

**Date:** 2026-05-25
**Branch:** `feature/carb-estimation-uncertainty`
**Scope:** `sim_user_insights/` pipeline + `app/t1d_companion/` + `app/food/`

## Pipeline Overview

```
User Input
  → stage_select_profile    (random anchor + CGM reading)
  → stage_parse_foods       (LLM + regex fallback → ParsedFood[])
  → stage_db_lookup         (food search → evidence + ranges)
  → stage_decide_clarification  (uncertainty thresholds)
  → [interactive? → ask user → stage_apply_clarification → re-run db_lookup]
  → stage_forecast          (deterministic glucose forecast)
  → stage_companion_advice  (LLM response with ranges + confidence)
  → Response
```

Each stage is a pure function: `stage(input_state) → output_state`. The `CompanionState` dataclass carries all context (12-Factor pattern).

## Candidate 1: LLM Service — Provider-Agnostic Adapter Seam

**Strength:** Strong
**Seam type:** Ports & adapters

**Files:** `app/services/llm_service.py` (1,133 LOC)

**Problem:** `LLMService` has 6 provider methods (`_call_openrouter`, `_call_minimax`, `_call_openai`, `_call_ollama`, `_call_deepseek`, `_call_google`) that duplicate HTTP setup, error handling, and response parsing. The interface is as complex as the implementation — shallow. Adding a new provider means copy-pasting ~50 lines.

**Solution:** Extract a `ProviderAdapter` interface with a single `execute(messages, config) → LLMResponse` seam. Providers become adapters registered in a dict. The 6 existing methods collapse into thin delegators.

**Wins:**
- **leverage:** one `execute()` interface, N providers
- **locality:** new adapter = one file, zero changes to `LLMService`
- **testability:** mock the adapter interface, not 6 HTTP clients
- **deletion test:** delete `_call_minimax` — complexity doesn't spread

## Candidate 2: LLM Call Wrapper — Capture `llm_call` Pattern

**Strength:** Strong
**Seam type:** In-process

**Files:** `companion_pipeline_v2.py` — `run_companion_pipeline` + `stage_parse_foods` + `stage_companion_advice`

**Problem:** `llm_call` is created as an inline closure in the pipeline runner and threaded as a parameter through 2+ stages. It can't be tested, logged, or swapped without modifying the pipeline runner. Token usage is discarded.

**Solution:** Extract `LLMCapture` as a callable module with a `(messages, max_tokens) → LLMResponse` interface. Tracks token usage, supports dry-run mode, and is mockable in stage tests.

**Wins:**
- **locality:** token logging and retry logic in one place
- **testability:** mock `LLMCapture`, not `LLMService` + `httpx`
- **leverage:** pipeline stages call `llm(messages)` — no provider awareness

## Candidate 3: Forecast Engine — Encapsulate as Stage

**Strength:** Worth exploring
**Seam type:** In-process

**Files:** `sim_user_insights/scripts/forecast_engine.py` (289 LOC) → `stage_forecast` in `companion_pipeline_v2.py`

**Problem:** Per-anchor calibration constants (OU drift rate, Gaussian σ, balance factors) are scattered across `PatientConfig` fields. `stage_forecast` reads these ad-hoc. No single place to understand the forecast model.

**Solution:** Create a `ForecastStage` that encapsulates both the calibration config and the `forecast_glucose` function. It becomes a deep module: `forecast(state) → Forecast` hides OU math, kernel calibration, and per-anchor parameter selection.

**Wins:**
- **locality:** all forecast calibration in one module
- **testability:** inject a `MockForecastStage`, test pipeline isolation
- **leverage:** swap forecast models without touching pipeline stages

## Candidate 4: Food Search — Unify Semantic + Lexical Candidates

**Strength:** Worth exploring
**Seam type:** In-process

**Files:** `app/food/service.py` — `_search_local_off` (3 code paths)

**Problem:** Lexical and semantic search are separate code paths called sequentially. Semantic search is dead code at runtime (embed_call is None, caught by except). Duplicated result formatting between paths.

**Solution:** Unify into a `FoodSearch` facade with strategy adapters. Lexical strategy uses ILIKE + trigram (current fast path). Semantic strategy uses pgvector when embeddings available. Merge strategy runs both and deduplicates. All paths produce the same candidate dict format with `_semantic_sim` populated.

**Wins:**
- **leverage:** one `search_food_candidates` interface, swappable strategy
- **testability:** mock `FoodSearch`, test scoring in isolation from DB
- **depth:** complex search logic (ILIKE + pgvector + merge + sort) behind small interface

## Candidate 5: Pipeline Runner — Declarative Stage Graph

**Strength:** Speculative
**Seam type:** In-process

**Files:** `companion_pipeline_v2.py` — `run_companion_pipeline` + `main`

**Problem:** `run_companion_pipeline` mixes LLM client creation, stage sequencing, and the interactive clarification loop. Adding a new stage requires understanding the whole function. The stage graph is implicit in call order.

**Solution:** Make the pipeline a declarative stage graph: `[Stage(select_profile), Stage(parse_foods, needs_llm=True), ...]`. A `PipelineRunner` executes stages in order, injecting dependencies where declared. Interactive mode becomes a `ClarificationWrapper` around `db_lookup`.

**Wins:**
- **locality:** stage order in one data structure, not spread across function calls
- **testability:** test `PipelineRunner` with mock stages, no DB or LLM needed
- **leverage:** add/remove/reorder stages without changing orchestration code

## Top Recommendation

**Candidate 1: LLM Service — Provider-Agnostic Adapter Seam**

This is the strongest candidate because the interface change is well-bounded, the duplication is obvious, and the locality gains are immediate. The other candidates (LLMCapture, ForecastStage, FoodSearch facade) all depend on or benefit from having a clean LLM adapter seam first. Starting here creates a clean adapter seam that the LLMCapture module can target, rather than the current mix of direct `_call_llm` calls threaded through closures.
