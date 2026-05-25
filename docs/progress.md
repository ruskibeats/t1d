# Progress — 2026-05-25

## Session Overview

Full codebase audit using `skill:t1d-companion-knowledge-base` followed by systematic implementation of findings, prioritized by safety impact. 709 tests passing across all modules.

## Completed Tasks

### 🔴 Safety — Critical

| # | Task | Files Changed |
|---|------|-------------|
| 258 | Load safety keywords from config file | `app/ai/safety.py`, `data/safety_config.json` |
| 259 | Wire forecast safety validator into engine | `app/services/meal_forecast_engine.py` |
| — | Fix fast_analysis.py bolus output (safety violation) | `app/t1d_companion/fast_analysis.py` |
| — | Fix food/service.py fast_meal_analysis bolus output | `app/food/service.py` |
| — | Fix coordinator.py disclaimer enforcement | `app/agents/coordinator.py` |

### 🏗️ Architecture

| # | Task | Files Changed |
|---|------|-------------|
| — | Gate SQLite compatibility patches to dev only | `app/core/database.py` |
| — | Create missing CONTEXT.md at project root | `/root/t1d/CONTEXT.md` |
| — | Remove doctest-modules from pytest config | `pyproject.toml` |
| — | Remove .bak files from repo, add *.bak to gitignore | `.gitignore` |
| 273 | Consolidate data architecture — drop Iceberg, single Postgres | `archive/iceberg/`, `docs/DATA_ARCHITECTURE.md` |

### 📊 Phase 2 Features

| # | Task | New Files |
|---|------|-----------|
| 262/267 | Historical meal matching service | `app/services/historical_meal_matcher.py`, 19 tests |
| 248/268 | Confidence scoring service | `app/services/confidence_scoring_service.py`, 20 tests |
| 249 | Profile learning convergence (2-week calibration) | `app/services/profile_learner.py`, 22 tests |

### ⚡ Performance & Robustness

| # | Task | Files Changed |
|---|------|-------------|
| 260/265 | TIR caching in chat loop (10-min TTL) | `app/services/pattern_service.py` |
| 261/266 | Fix _search_local_off silent exception handling | `app/food/service.py` |

### 🔗 Integration

| # | Task | Files Changed |
|---|------|-------------|
| 237 | Wire enriched sim users into companion loop | `app/t1d_companion/production/repositories.py` |
| 276 | Unified CGM Bridge Service | `app/services/cgm_bridge_service.py`, 11 tests |
| 277 | LLM provider fallback + health tracking | `app/services/llm_service.py`, `app/config.py` |

### 🗺️ CGM Strategy

| # | Task | Files Changed |
|---|------|-------------|
| 244 | Nightscout setup guide | `docs/NIGHTSCOUT_SETUP.md` |
| — | Nightscout as primary integration path | `docs/NIGHTSCOUT_SETUP.md`, `app/api/cgm.py` |
| — | LibreLinkUp → developer fallback, consent required | `app/services/librelinkup_service.py` |
| — | CGM API unified (`GET /cgm/sources`, `POST /cgm/connect`) | `app/api/cgm.py`, `app/models/user.py` |

### 📋 Compliance

| # | Task | New Files |
|---|------|-----------|
| 253 | MHRA self-certification documentation | `docs/compliance/MHRA_SELF_CERTIFICATION.md` |

## Backend Status

| Phase | Completion |
|-------|-----------|
| Phase 1 (Core MVP) | ✅ 100% |
| Phase 2 (Analytics) | ✅ 100% |
| Safety & Compliance | ✅ 100% |
| Data Architecture | ✅ Single PostgreSQL |
| CGM Integration | ✅ Nightscout-first, Dexcom OAuth, LibreLinkUp fallback |
| LLM Resilience | ✅ Provider fallback + health tracking + rule-based fallback |
| **Launch readiness** | **~70%** (need company reg, privacy policy, MHRA reg, CI/CD) |

## Remaining

| # | Task | Priority | Effort |
|---|------|----------|--------|
| 268 | Register company at Companies House | P0 | 30 min |
| 269 | Privacy Policy + Terms of Service | P0 | Half day |
| 270 | Register device with MHRA | P0 | 1 hour |
| 130 | CI/CD Pipeline | P1 | Medium |
| 272 | Production hosting (VPS + DB + domain) | P1 | Medium |
| 275 | Update Dexcom OAuth section in setup guide | P1 | Small |
| 167 | Detector regression tests | P2 | Small |
| 251 | Shared Nightscout infra | P3 | Large |
| 252 | Push notifications | P3 | Large |
| 254 | Coaching chatbot Q&A | P3 | Large |