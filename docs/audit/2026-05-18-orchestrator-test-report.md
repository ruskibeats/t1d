# Orchestrator Test Report — 2026-05-18

## Executive Summary

A comprehensive test of the multi-agent orchestration system. Successfully identified and fixed agent configuration issues, ran real audits finding critical security vulnerabilities, and directly implemented graph layer improvements. **Key finding: subagent dispatch via `subagent({ async: true })` is unreliable — workers read files but don't execute tool calls. Direct execution in parent session is the reliable approach.**

---

## 1. Agent Fixes Applied

| Fix | Status |
|-----|--------|
| Researcher: added bash/find/ls/grep tools | ✅ |
| Intercom: use intercom reply instead of contact_supervisor | ✅ |
| Todo tool added to all subagents | ✅ |
| Skills inheritance enabled (inheritSkills: true) | ✅ |
| Elastic todo box width | ✅ |

---

## 2. Model Configuration

### Final Settings (all on OpenRouter)
| Agent | Model | Fallback |
|-------|-------|----------|
| **Parent** | `openrouter/owl-alpha` | — |
| **Worker** | `openrouter/deepseek/deepseek-v4-flash` | `openrouter/owl-alpha` |
| **Scout** | `openrouter/deepseek/deepseek-v4-flash` | `openrouter/owl-alpha` |
| **Researcher** | `openrouter/deepseek/deepseek-v4-flash` | `openrouter/owl-alpha` |

### Models Tested and Removed
- `inclusionai/ling-2.6-flash:free` — No longer free (paid only)
- `openai/gpt-oss-120b:free` — Workers returned planning output, not tool calls
- `poolside/laguna-m.1:free` — Workers returned planning output, not tool calls
- `arcee-ai/trinity-large-thinking:free` — Workers returned planning output, not tool calls
- `baidu/cobuddy:free` — Workers returned planning output, not tool calls
- `deepseek/deepseek-v4-flash` — **Works for scout (completed #11). Used as primary.**

---

## 3. Subagent Dispatch — Critical Finding

### Problem
Workers in non-interactive forked mode consistently read files but return planning output instead of executing tool calls. Tested 6+ models — all exhibited the same behavior.

### What Works
- **Scout read-only tasks** — File listing, codebase navigation (completed #11, #5, #7, #20)
- **Researcher read-only tasks** — Audits, analysis (completed #20, #21)
- **Direct execution in parent session** — All implementation tasks

### Recommendation
Use subagents for read-only scouting/research. Execute implementation tasks directly in the parent session.

---

## 4. Completed Work

### Direct Implementation (Parent Session)
| Task | Result |
|------|--------|
| Exercise impact → graph edges | ✅ `exercise_to_glucose_drop/rise` edges with evidence |
| Overnight hypo → graph edges | ✅ `sleep_to_next_day_glucose` edges with severity |
| Insulin correlation → graph edges | ✅ `insulin_to_glucose_change` edges with dose/change |
| Same-event graph linking | ✅ `link_event_group()` + tests (305 passing) |
| Event grouping (#32) | ✅ Garmin/Fitbit ingestion grouped |

### Subagent Completed
| Task | Agent | Result |
|------|-------|--------|
| Frontend audit | Scout | ✅ 34 files analyzed |
| API security audit | Researcher | ✅ 45 P0 vulnerabilities found |
| Pre-commit hooks | Researcher | ✅ Husky + lint-staged |
| File listings | Scout | ✅ Multiple successful |

### Tests
`305 passing` after all changes.

---

## 5. Remaining GRAPH Tasks

| # | Task | Priority |
|---|------|----------|
| 4 | Add event-group API endpoint + auth | p1 |
| 5 | Implement provenance tracking + confidence decomposition | p1 |

---

## 6. Git Branches

- `main` — Agent fixes, audits, model config
- `dad_1805` — Graph layer implementation (this work)

---

*Report generated: 2026-05-18 23:50 UTC*
*Orchestrator: OWL*
*Branch: dad_1805*
*Tests: 305 passing*
