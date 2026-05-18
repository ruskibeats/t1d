# Orchestrator Test Report — 2026-05-18

## Executive Summary

A comprehensive test of the multi-agent orchestration system. Successfully identified and fixed several agent configuration issues, ran real audits that found critical security vulnerabilities, and established the `dad_1805` branch for graph layer development. **Key finding: subagent dispatch via `subagent()` async is unreliable with current models in non-interactive forked mode — workers read files but don't execute tool calls.**

---

## 1. Agent Fixes Applied

### 1.1 Researcher Tool Access ✅
**Problem:** Researcher lacked `bash`, `find`, `ls`, `grep` — could not run shell commands.
**Fix:** Added tools to `agents/researcher.md`. Researcher can now run commands directly.

### 1.2 Intercom in Non-Interactive Mode ✅
**Problem:** Subagents in non-interactive forked mode could not process intercom replies.
**Fix:** Updated all three agents to use `intercom({ action: "reply" })` with "BLOCKED:" prefix convention.

### 1.3 Todo Tool in Subagents ✅
**Problem:** Subagents could not update their own todo status.
**Fix:** Added `todo` tool to all three agents with instructions to mark in_progress/completed.

### 1.4 Skills Inheritance ✅
**Problem:** All agents had `inheritSkills: false`.
**Fix:** Changed to `inheritSkills: true` — agents now pick up project skills automatically.

### 1.5 Elastic Todo Box Width ✅
**Problem:** Fixed 72-char width caused truncation.
**Fix:** Updated `TodosView.render()` to use terminal width with proportional columns.

---

## 2. Model Configuration

### Final Settings (all on OpenRouter, all free)
| Agent | Model | Fallback |
|-------|-------|----------|
| **Parent** | `openrouter/owl-alpha` | — |
| **Worker** | `openrouter/deepseek/deepseek-v4-flash` | `openrouter/owl-alpha` |
| **Scout** | `openrouter/deepseek/deepseek-v4-flash` | `openrouter/owl-alpha` |
| **Researcher** | `openrouter/deepseek/deepseek-v4-flash` | `openrouter/owl-alpha` |

### Models Tested and Removed
- `inclusionai/ling-2.6-flash:free` — **No longer available as free** (paid only as of this session)
- `openai/gpt-oss-120b:free` — Tested but workers returned planning output instead of tool calls
- `nvidia/nemotron-3-super-120b-a12b:free` — Available but not tested in dispatch
- `z-ai/glm-4.5-air:free` — Available but not tested in dispatch
- `poolside/laguna-m.1:free` — Available but not tested in dispatch

---

## 3. Subagent Dispatch — Critical Finding

### Problem
When dispatching tasks via `subagent({ async: true })`, workers consistently:
1. Read the assigned files correctly
2. Returned planning/scratchpad output instead of executing tool calls
3. Completed without making any edits or running any commands
4. Required supervisor interrupt to stop

### Root Cause
The models in non-interactive forked context are not reliably executing tool calls. They treat the task as a "respond with a plan" rather than "execute these steps."

### Workaround
**Execute tasks directly in the parent session** rather than dispatching to subagents. The parent session has full tool access and can execute reliably.

### Recommendation for Human
- Subagent dispatch needs further investigation — possibly requires different model, different prompt structure, or synchronous mode
- For now, the orchestrator should execute tasks directly and only use subagents for truly independent parallel work
- Consider testing with `sync: true` instead of `async: true`

---

## 4. Completed Work

### Test Batches (All Completed ✅)
| # | Task | Result |
|---|------|--------|
| 1-3 | Smoke tests (create files, count lines) | ✅ All passed |
| 4-8 | Parallel dispatch (list files, git log) | ✅ All passed |
| 10-14 | Mixed simple tasks | ✅ All passed |
| 18 | Pre-commit hooks setup | ✅ Husky + lint-staged installed |
| 20 | Frontend unused component audit | ✅ 34 files analyzed, cleanup candidates identified |
| 21 | API endpoint validation audit | ✅ **P0: 45 unauthenticated endpoints found** |

### Real Deliverables
1. **Pre-commit hooks** — Husky v9 + lint-staged configured for frontend
2. **API Security Audit** — Found ~45 unauthenticated endpoints (P0), ~30 missing input validation (P1), ~20 weak error handling (P2)
3. **Frontend Audit** — Found 3 empty directories, 10 unused interfaces, 12 unused hook exports
4. **Agent Coordinator ADR** — Documented at `docs/adr/001-agent-coordinator.md`
5. **Orchestrator Test Report** — This document

---

## 5. GRAPH_TODO Status

The `plan/todos/GRAPH_TODO.md` contains 15 actionable items for the graph layer. These were broken into todos #31-#45 but **none were successfully dispatched to subagents** due to the dispatch issue above.

### What's Already Done in Codebase
- `event_group_id` column exists in `HealthMetric` model
- `event_group_id` in `HealthMetricCreate` and `HealthMetricResponse` schemas
- `event_group_id` passed in `HealthMetricService.create()` and `create_batch()`
- `HealthMetricEdge` model and `GraphEdgeType` enum exist
- `HealthGraphService` with basic methods exists
- Graph API endpoints exist at `/api/v1/metrics/graph/...`
- RAG context includes graph edges

### What Still Needs Work (from GRAPH_TODO)
1. **Event grouping logic** — Assign event_group_id during ingestion (meals, exercise, sleep, insulin)
2. **Same-event graph linking** — Create `same_event_as` edges
3. **Schema extensions** — Add window_start/window_end/confidence_components/provenance to edges
4. **Migrations** — Alembic migration for new columns
5. **Pattern wiring** — Delayed meal, exercise, overnight, insulin edge detection
6. **Provenance tracking** — Detector name/version/run type on edges
7. **Confidence decomposition** — Component scoring utility
8. **Photo meal ingest** — Visual detector research and service contract
9. **Tests** — Event grouping, pattern edges, provenance, confidence, safety
10. **Documentation** — Update CONTEXT.md, ARCHITECTURE_MAP.md

---

## 6. Git Branches

- `main` — Contains orchestrator fixes, audits, model config
- `dad_1805` — Contains GRAPH_TODO breakdown (15 todos created but not dispatched)

---

## 7. Key Learnings

1. **Model reliability > model capability** — A smaller model that executes tool calls is better than a larger model that only plans
2. **Non-interactive forked mode is unreliable** — Subagents need either sync mode or different model/prompt approach
3. **Direct execution works** — The parent session can execute all tasks reliably
4. **Audit subagents work well** — Scout and researcher completed complex audits (#20, #21) when given focused read-only tasks
5. **Intercom escalation works** — When subagents can't complete tasks, they escalate via intercom correctly
6. **Skills inheritance is valuable** — Enabling `inheritSkills: true` gives agents access to project-specific skills automatically

---

## 8. Recommendations for Human

1. **Review subagent dispatch approach** — Consider sync mode, different models, or direct execution
2. **Prioritize API security fixes** — 45 unauthenticated endpoints is a P0 vulnerability
3. **Execute GRAPH_TODO directly** — The 15 graph tasks are ready to execute in parent session
4. **Clean up test artifacts** — hello.txt, goodbye.txt, timestamp.txt, notes.txt, README_extra.md
5. **Consider model strategy** — Pick 2-3 reliable free models and stick with them; don't chase the latest model

---

*Report generated: 2026-05-18 22:30 UTC*
*Orchestrator: OWL*
*Branch: dad_1805*
