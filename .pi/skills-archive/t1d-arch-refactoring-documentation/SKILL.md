---
name: "t1d-arch-refactoring-documentation"
description: "Document architectural refactoring work in T1D Companion: create ADR, update CONTEXT.md glossary, write plan audit with verification, verify no remaining consumers of deprecated code, and present summary with measurable impact metrics. Use when completing any architectural refactoring task."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Document Architectural Refactoring Completion

## When to Use
After completing an architectural refactoring task in T1D Companion (e.g., MetricRegistry deepening, dual-write consolidation, service pattern changes). Use when the user says "document it all" or when finishing a refactoring task.

## Procedure

### 1. Create Architecture Decision Record (ADR)
Create `docs/adr/NNN-title.md` with:
- **Title**: [NNN] Short descriptive title
- **Status**: Accepted
- **Context**: What problem existed, what patterns were duplicated
- **Decision**: What was built, why this approach
- **Consequences**: Table with metrics (LOC removed, flush count reduction, service count, test coverage)
- **Migration Patterns**: Before/after code examples showing the pattern change
- **Migration Checklist**: Table of all services migrated, with batch vs single mode, and verification status

### 2. Update CONTEXT.md Glossary
Add new domain terms to the glossary section:
- **NewTerm**: Definition with Avoid label if applicable
- Reference the ADR number in the definition

### 3. Update the Clanker Ops Plan File
Update `.pi/todo-plans/#N_plan.md`:
- Set Status to `completed` (or in_progress if partially done)
- Add **Audit** section with:
  - Files changed (created/modified)
  - Tokens consumed
  - Test results (pass/fail counts)
  - Verification steps completed

### 4. Final Verification
Run these commands to confirm completeness:
```bash
# 1. No remaining imports of deprecated code
grep -rn "import.*old_module\|from.*old_module" app/*/service.py

# 2. All services use new pattern
grep -rn "import.*new_module\|from.*new_module" app/*/service.py

# 3. Full test suite passes
cd /root/t1d && python3 -m pytest --tb=short -q

# 4. File size is healthy (not collapsed)
wc -c .pi/todo-state.json
```

### 5. Present Summary
Report to user with:
- What was created and modified
- Impact metrics (e.g., "14 services refactored, 67% LOC reduction, 7x fewer flushes")
- Test results
- "All tasks completed" confirmation

## Pitfalls
- **Don't skip the ADR**: The user expects formal documentation for architectural decisions
- **Don't forget to verify deprecated code has no remaining consumers**: `grep -rn` for imports before declaring deprecation complete
- **Don't skip CONTEXT.md updates**: New domain terms need glossary entries
- **Don't present incomplete work**: Always run full test suite, not just the new tests
- **Don't miss the plan file audit**: The plan file must be updated with verification results

## Verification
1. ADR exists at `docs/adr/NNN-title.md`
2. CONTEXT.md glossary has new terms
3. Plan file has completed status + Audit section
4. Full test suite passes (all tests, not just new ones)
5. No remaining consumers of deprecated code (confirmed via grep)
6. Summary with impact metrics shared with user