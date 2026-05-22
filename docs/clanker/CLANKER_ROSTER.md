# Clanker Roster

*A comprehensive guide to available agents for task allocation*

---

## Built-in Agents (Default)

### `planner`
**Purpose:** Creates implementation plans from context and requirements  
**Use for:** Breaking down complex tasks, creating structured implementation plans  
**Context mode:** fork  
**Example usage:** Generate a plan for implementing a new feature, decompose epics into tasks

### `worker`
**Purpose:** Implementation agent for normal tasks  
**Use for:** Writing code, implementing features, making changes  
**Context mode:** fork  
**Example usage:** Write a new API endpoint, implement a service class, build a React component

### `researcher`
**Purpose:** Autonomous web researcher — searches, evaluates, and synthesizes research briefs  
**Use for:** Investigating solutions, finding documentation, comparing approaches  
**Example usage:** Research best practices for OAuth2, find FastAPI async patterns

### `reviewer`
**Purpose:** Versatile review specialist for code diffs, plans, and proposed solutions  
**Use for:** Code review, plan review, verifying work matches spec  
**Example usage:** Review a PR, check if implementation matches requirements

### `oracle`
**Purpose:** High-context decision-consistency oracle that protects inherited state  
**Use for:** Complex multi-step tasks requiring consistency, protecting state across operations  
**Context mode:** fork  
**Example usage:** Long-running refactors, multi-file coordination tasks

### `delegate`
**Purpose:** Lightweight subagent that inherits parent model with no default reads  
**Use for:** Simple delegation without heavy context loading  
**Example usage:** Quick code snippets, simple formatting tasks

### `scout`
**Purpose:** Fast codebase reconnaissance that returns compressed context for handoff  
**Use for:** Exploring unfamiliar code, finding relevant files, understanding architecture  
**Example usage:** "Where is the graph edge persistence implemented?"

### `context-builder`
**Purpose:** Analyzes requirements and codebase, generates context and meta-prompt  
**Use for:** Setting up context for complex tasks, understanding what files/models are needed  
**Example usage:** Before starting a major feature, understand all dependencies

---

## Project Agents (T1D-Specific)

### `phase1-agent-coordinator`
**Purpose:** Wires up the T1D Companion agent coordinator  
**Use for:** Implementing Phase 1 agent coordination in `app/agents/coordinator.py`  
**Files:** `app/agents/coordinator.py`

### `phase1-chat-rag`
**Purpose:** Fixes T1D Companion chat endpoint and RAG pipeline  
**Use for:** Implementing Phase 1 chat pipeline, connecting LLM to agent system

### `phase1-integration-tests`
**Purpose:** Writes integration tests for chat pipeline  
**Use for:** Testing full flow: register, login, chat, safety checks, emergency escalation

### `phase1-llm-fallback`
**Purpose:** Adds rule-based fallback response generator  
**Use for:** Making chat pipeline work end-to-end without API keys

### `phase2-pattern-tests` / `phase2-pattern-tests-v2`
**Purpose:** Comprehensive unit tests for PatternService  
**Use for:** TIR calculation, spike detection, overnight hypoglycemia, exercise impact

### `phase2-safety-llm-tests` / `phase2-safety-llm-tests-v2`
**Purpose:** Unit tests for SafetyScaffold and LLMService  
**Use for:** Policy violations, provider fallback, prompt building, context assembly

### `phase3-dexcom-nightscout` / `phase3-dexcom-nightscout-v2`
**Purpose:** Implements Dexcom OAuth callback and Nightscout config API  
**Use for:** Phase 3 data ingestion - connecting external CGM providers

### `phase3-food-providers` / `phase3-food-providers-v2`
**Purpose:** Implements OpenFoodFacts and USDA FoodData Central API clients  
**Use for:** Phase 3 food database integration

### `fixer-wave1` / `fixer-wave2`
**Purpose:** Review reports and apply fixes to identified issues  
**Use for:** Post-review cleanup, fixing conflicts between parallel workers

### `reviewer-wave1` / `reviewer-wave2`
**Purpose:** Reviews code changes from parallel workers  
**Use for:** Verifying correctness, edge cases, import errors, style consistency

---

## Engineering Skills (Reusable Procedures)

### Code Implementation
| Skill | Purpose | Use Case |
|-------|---------|----------|
| `diagnose` | Disciplined bug diagnosis loop | Debug failing tests, performance regressions |
| `prototype` | Build throwaway prototypes | Sanity-check data models, mock up UIs |
| `tdd` | Test-driven development | Red-green-refactor loop, integration tests |
| `improve-codebase-architecture` | Find refactoring opportunities | Consolidate modules, improve testability |
| `review` | Review changes against standards/spec | Code quality, spec compliance |

### Project Planning & Triage
| Skill | Purpose | Use Case |
|-------|---------|----------|
| `to-issues` | Break plans into tracker issues | Convert PRD to GitHub issues |
| `grill-me` | Stress-test plans/designs | Validate architecture decisions |
| `grill-with-docs` | Challenge plans against domain model | Refine terminology, update docs |

*(Removed: `zoom-out`, `handoff`, `to-prd`, `triage`, `zoom-out` - less frequently used)*

### Documentation & Writing (Curated)

| Skill | Purpose | T1D Use Case |
|-------|---------|--------------|
| `edit-article` | Improve articles/prose | Clarify documentation |
| `ubiquitous-language` | Extract DDD glossary | Define domain terms |

*(Removed: `writing-beats`, `writing-fragments`, `writing-shape`, `setup-*` skills - one-time use or not core)*

---

## Design & UI Agents (Curated for T1D)

| Agent | Purpose | T1D Use Case |
|-------|---------|--------------|
| `impeccable` | UI polish, critique, optimization | Audit dashboard, fix cognitive load |
| `design-taste-frontend` | Senior UI/UX architecture | Override LLM biases, metric-based design |
| `minimalist-ui` | Clean editorial interfaces | Professional, content-focused UIs |
| `redesign-existing-projects` | Upgrade existing UIs | Modernize current frontend |

*(Removed: `industrial-brutalist-ui`, `stitch-design-taste`, `gpt-taste`, `high-end-visual-design`, `brandkit`, `image-to-code`, `imagegen-frontend-web`, `imagegen-frontend-mobile` - not core to T1D project)*

---

## Specialized Domain Agents (Curated for T1D)

| Agent | Purpose | T1D Use Case |
|-------|---------|--------------|
| `build-health-pattern-detection-engine` | Glucose pattern detection | Post-meal spikes, overnight hypo |
| `build-cgm-data-sync-service` | Dexcom/Nightscout sync | CGM data ingestion |
| `build-multi-provider-llm-rag-service` | LLM with RAG context | Grounded responses from health data |
| `build-vision-food-photo-analyzer-agent` | Food photo analysis | Carbs estimation from meal photos |
| `build-unified-health-metrics-store` | Health metric architecture | Unified time-series storage |
| `build-structured-ai-agent-infrastructure` | AI agent framework | Structured LLM output |
| `build-polymorphic-event-store` | Event logging system | Meals, insulin, exercise events |

*(Removed: `healthkit` - iOS-specific, not used in Python backend)*

---

## Task Allocation Guidelines

### For **Backend/Backend-Logic** Tasks:
1. **`worker`** - Implementation work
2. **`scout`** - Codebase reconnaissance first
3. **`diagnose`** - Debugging failing code
4. **`review`** - Code quality check

### For **Frontend/UI** Tasks:
1. **`impeccable`** - Design critique/polish
2. **`minimalist-ui`** - Clean interface design
3. **`industrial-brutalist-ui`** - Data-heavy dashboards
4. **`design-taste-frontend`** - Architecture decisions

### For **Testing** Tasks:
1. **`tdd`** - Red-green-refactor test development
2. **`phase2-pattern-tests`** - Pattern service tests
3. **`phase1-integration-tests`** - E2E chat pipeline tests

### For **Research/Planning** Tasks:
1. **`planner`** - Create implementation plans
2. **`researcher`** - Web research and synthesis
3. **`scout`** - Codebase exploration
4. **`grill-me`** - Stress-test ideas

### For **Documentation** Tasks:
1. **`grill-with-docs`** - Update docs inline
2. **`ubiquitous-language`** - Define domain terms
3. **`edit-article` | Improve prose quality

---

## Agent Assignment Quick Reference

```
# For complex tasks, chain:
planner → worker → reviewer → fixer-wave

# For research:
researcher → scout → planner

# For bugs:
diagnose → worker → review

# For design:
design-taste-frontend → impeccable → review
```

---

## Agent Pruning Summary

**Original roster:** 62 agents  
**Curated roster:** ~35 agents  
**Reduction:** 44% fewer agents, higher signal-to-noise

**Removed categories:**
- iOS-specific (`healthkit`)
- Content writing (`writing-fragments`, `writing-beats`, `obsidian-vault`)
- Overly specialized design (`brandkit`, `stitch-design-taste`, `gpt-taste`)
- Image generation (`imagegen-*`, `image-to-code`)
- Claude Code specific (`git-guardrails-claude-code`)

**Kept criteria:**
1. Directly relevant to T1D Companion backend/frontend
2. No overlapping functionality
3. Used in current or planned sprint work

---

*Updated: 2026-05-19*  
*For current agent availability, run: `pi subagent list`*
---

## Human Collaborators

### Tom (@tom_웃)
**Role:** Data Engineer, Certified Scrum Master, T1D Enthusiast  
**Skills:** Scrum, Data Pipelines, SQL, PySpark, Progress Tracking, Team Coordination  

**Strengths for T1D Companion:**
- Sprint planning & progress tracking (`#20`)
- Scrum Master for development workflow
- Data pipeline design (PySpark/Azure background)
- Documentation alignment sprints

**Recommended tasks:**
- `#20` Review progress.md and update sprint priorities
- Sprint milestone planning and retrospectives
- Documentation alignment (Scrum-of-one for docs)

**Interview:** `.pi/todo-plans/human-interview-template.md`

### Assignee Tags & Glyphs

| Role | Assignee | Glyph | Type | Color |
|------|----------|-------|------|-------|
| Implementation | `@worker` | `_` suffix | droid | `warning` (amber) |
| Sprint execution | `@builder` | `_` suffix | droid | `warning` (amber) |
| Codebase recon | `@scout` | `_` | `_` suffix | droid | `warning` (amber) |
| Research | `@researcher` | `_` suffix | droid | `warning` (amber) |
| Code review | `@reviewer` | `_` suffix | droid | `warning` (amber) |
| Planning | `@planner` | `_` suffix | droid | `warning` (amber) |
| Human | `@tom_웃` | `웃` suffix | human | `accent` (cyan) |
| Human | any `@name_웃` | `웃` suffix | human | `accent` (cyan) |

**Glyph rule:** Droids use `@name`. Humans use `@name_웃` (U+C6C3, Hangul "us", meaning *smile*).

### Model Routing

All subagent roles use `openrouter/owl-alpha`. Always `async: true`, `context: "fork"`, `cwd=/root/t1d`.

### Color Coding (Clanker Ops Board)

After `/reload`, the Clanker Ops extension renders:
- Droid assignees in `warning` color (amber/yellow)
- Human assignees (`웃` suffix) in `accent` color (cyan/highlight)

Human tasks also carry a `🧑` tag for additional visual distinction.

### Audit & EOD Reporting

Every plan file (`.pi/todo-plans/#N_plan.md`) ends with an `## Audit` section requiring agents to report:
1. Files created or modified (full paths)
2. Verification results
3. Gaps or findings discovered
4. Decision made (model, approach, tradeoffs)
5. Estimated tokens used

**Integrity rule:** Agents must never change task assignees. `@researcher`, `@builder`, `@scout`, `@tom_웃` are all valid.

### Current Allocation

| # | Item | Assignee | Priority |
|---|------|----------|----------|
| 1 | [GRAPH-A] Exercise/sleep/insulin edges | `@worker` | p0 ✅ |
| 2 | [GRAPH-B] Provenance tracking | `@researcher` | p1 |
| 10 | Sprint 2: Frontend Screen Consolidation | `@builder` | p1 |
| 11 | Sprint 3: Security + Deployment Hardening | `@builder` | p1 |
| 12 | Sprint 4: Code Quality + Provider Showcase | `@builder` | p1 |
| 13 | Sprint 5: CI/CD + Launch Prep | `@builder` | p1 |
| 14 | Event grouping foundation | `@tom_웃` | p0 ✅ |
| 16 | Delayed high-fat meal detection edges | `@worker` | p1 |
| 19 | Photo meal ingest MVP | `@researcher` | p1 |
| 20 | Review progress.md | `@tom_웃` | — |
| 23 | Event-group endpoint (merged #31) | `@worker` | p1 |
| 24 | Food resolution service | `@researcher` | p1 |
| 28 | EOD reporting | unassigned | — |
| 29 | Review Google Stitch design | `@tom_웃` | — |
| 32 | Auth migration (13 routes) | `@worker` | p1 |
| 35 | Update CONTEXT.md graph definitions | `@worker` | p1 |

### Reference

- **Allocation manual:** `.pi/CLANKER_OPS_SUBAGENT_ALLOCATION.md`
- **Model routing:** `.pi/agents/MODEL-ROUTING.md`
- **Board state:** `.pi/todo-state.json`
- **EOD audit:** `.pi/EOD_AUDIT.md`
- **Extension:** `npm:pi-subagents` (nicobailon)
- **Todo extension:** `/root/.pi/agent/extensions/todo/index.ts`

### `butler`
**Purpose:** Clanker Ops housekeeper — board hygiene, audit, duplicate detection
**Use for:** EOD reports, plan audits, dupe combing, roster sync, housekeeping
**Context mode:** fresh
**Example usage:** `/run butler "audit plans"`, `/run butler "comb dupes"`, `/clanker eod`
**Key difference from other clankers:** Does NOT edit tasks or write code. Reports findings only.
