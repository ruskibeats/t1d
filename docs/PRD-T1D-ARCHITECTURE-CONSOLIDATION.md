# PRD: T1D Companion Architecture Consolidation
**Status:** Ready for Stakeholder Review  
**Date:** 2026-05-30  

---

## 1. Problem Statement

### Who has the problem?
- **Engineers**: Unclear where to implement changes (demo/ vs app/agents/)
- **Product**: Unclear what is production code vs experimental
- **Safety Team**: Multiple safety check layers with potential drift

### What is the problem?
The T1D Companion project has two parallel implementations:
- `demo/` — 7-stage pipeline with simulated data (production serving users)
- `app/agents/` — Multi-agent system with database integration (experimental)

Both stacks duplicate core logic (forecasting, safety, physiology) without clear ownership, leading to:
- Risk of inconsistent outputs
- Safety policy drift
- Confusion about canonical implementation paths

### Evidence it's real
- 481 files indexed in CodeGraph showing overlapping functionality
- `SafetyScaffold` and `SafetyAgent` both perform validation
- `demo/forecast_engine.py` and `app/prediction/engine.py` both forecast glucose
- Documentation showed "DECISION REQUIRED" for canonical runtime, schema, and safety authority

---

## 2. Solution

We have created canonical, enforceable architecture decisions:

### Canonical Schemas (`app/schemas/prediction.py`)
```python
class GlycemicPrediction(BaseModel):
    # REQUIRED
    predicted_glucose_mg_dl: int
    time_to_peak_minutes: int
    baseline_glucose_mg_dl: int
    confidence_tier: Literal["high", "medium", "low"]
    carb_estimate_total_g: float
    # OPTIONAL
    ascii_chart: str | None
    explanation_text: str | None
```

### Unified Safety Policy (`docs/SAFETY_POLICY.md` + `app/schemas/safety.py`)
- Single veto gate: `app/ai/safety.py` → `SafetyScaffold.validate()`
- Authoritative policy document listing allowed/blocked language
- `SafetyReview` Pydantic schema for programmatic checks

### Runtime Ownership (`demo/` canonical for 30 days)
- **Canonical**: `demo/companion_pipeline_v2` (proven production)
- **Target**: `app/agents/` (next-gen, experimental)
- **Bridge**: `app/services/*` shared by both stacks

### Verification Pipeline (`Makefile`)
```bash
make verify        # All checks
make verify-schemas # Pydantic validation
make verify-safety  # Safety gate testing
```

---

## 3. User Stories

| Role | Can | Outcome |
|------|-----|---------|
| Engineer | Edit only in `app/prediction/engine.py` | Forecast logic converges across stacks |
| Engineer | Run `make verify` before PR | Drift prevented by CI |
| Safety Officer | Update `docs/SAFETY_POLICY.md` | Policy changes without code deploy |
| Developer | Import `GlycemicPrediction` schema | Single contract for predictions |
| Product Manager | Know `demo/` is canonical | Clear migration timeline |

---

## 4. Implementation Decisions

### Technical Choices Made
1. **Schemas**: Pydantic (compatible with both demo and app)
2. **Safety**: Externalized config pattern (`data/safety_config.json` fallback to `_DEFAULT_CONFIG`)
3. **State**: Both `CompanionState` and `CoordinatorContext` maintained (serialize to JSON)
4. **Files Created**:
   - `app/schemas/prediction.py` — Canonical prediction contract
   - `app/schemas/safety.py` — Safety review schema  
   - `docs/SAFETY_POLICY.md` — Authoritative policy rules
   - `Makefile` — Verification commands

### Trade-offs Considered
- **Converged schemas now** vs **Let drift continue** — Chose convergence to prevent future conflicts
- **Single safety layer** vs **Multiple layers** — Chose single veto gate for consistency
- **Merge now** vs **Canonical + migration path** — Chose canonical + 30-day window for stability

---

## 5. Testing Decisions

### Validation Methods
- Schema import tests (Pydantic validation)
- Safety language blocking tests
- `make verify` pipeline for pre-PR checks

### Acceptance Criteria (DoD)
| Phase | Metric | Pass Condition |
|-------|--------|---------------|
| Phase 1 | Safety | `SafetyScaffold.validate()` blocks all dosing language |
| Phase 2 | Schema | 100% of responses serialize to `GlycemicPrediction` |
| Phase 3 | Integration | Demo and App outputs match on all 12 profiles |

---

## 6. Out of Scope

- **State object unification** — Both `CompanionState` and `CoordinatorContext` remain separate
- **Food history backend** — Still using bootstrap JSON, not migrated to DB
- **Real-data calibration** — Simulator-only for now, Nightscout validation deferred

---

## 7. Further Notes

### Dependencies
- Pydantic >= 2.0
- Python 3.11+ (for `str | None` syntax)

### Risks
- Low: Safety layer changes may require immediate rollback
- Medium: Schema changes downstream will need migration

### Follow-up Work
- Phase 2: Integrate `PredictionEngine` into demo pipeline
- Phase 3: Compare outputs on real Nightscout data
- Consider: Auto-generate `GlycemicPrediction` from actual demo output