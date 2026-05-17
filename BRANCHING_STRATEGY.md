# Branching Strategy for T1D Companion

## Current State
- ✅ Git initialized
- ✅ Currently on `main` branch
- ⚠️ No branches exist yet — all work goes straight to `main`

## Recommended Workflow: GitHub Flow (Simple & Effective)

For a project of this size (single developer or small team), **GitHub Flow** is the best fit — simpler than Git Flow, no long-running branches, no `develop` branch overhead.

```
main  ──●────●────●────●────●──────────────────────●──
          \        /          \        /
feature-1  ●──●──●            ●──●──●
                                   \
fix-branch                           ●──●──●
```

### Core Rules

| Rule | Why |
|------|-----|
| **Never commit directly to `main`** | Prevents broken code in production |
| **Every change gets a branch** | Isolates work, enables review |
| **Branch names describe the work** | Self-documenting |
| **Merge via Pull Request** | Enables review and CI checks |
| **Delete branches after merge** | Keeps repo clean |

---

## Branch Naming Convention

Use a consistent prefix system so branches are sortable and identifiable:

```
<type>/<short-description>
```

### Types

| Prefix | When to Use | Example |
|--------|-------------|---------|
| `feat/` | New feature or enhancement | `feat/dexcom-oauth-flow` |
| `fix/` | Bug fix | `fix/stream-endpoint-crash` |
| `docs/` | Documentation changes | `docs/api-usage-examples` |
| `refactor/` | Code restructuring (no behavior change) | `refactor/consolidate-safety` |
| `test/` | Adding or fixing tests | `test/pattern-service-coverage` |
| `chore/` | Maintenance, config, deps | `chore/update-dependencies` |
| `perf/` | Performance improvements | `perf/optimize-glucose-queries` |

### Naming Examples for T1D

```
feat/wire-agent-coordinator
feat/dexcom-oauth-callback
fix/rule-based-fallback-crash
fix/duplicate-safety-check
refactor/consolidate-safety-scaffold
refactor/normalize-timezone-handling
test/pattern-service-unit-tests
test/chat-pipeline-integration
docs/update-plan-with-progress
chore/add-ci-pipeline
perf/fix-n-plus-one-user-queries
```

---

## Workflow Steps

### 1. Create a Branch

```bash
# Make sure you're on main and up to date
git checkout main
git pull origin main

# Create and switch to a new branch
git checkout -b feat/wire-agent-coordinator
```

### 2. Make Changes

```bash
# Work on your changes
# Stage and commit frequently (atomic commits)
git add app/agents/coordinator.py
git commit -m "Wire DataIngestionAgent to real LLMService.retrieve_context()"
git add app/agents/
git commit -m "Wire PatternAgent to real PatternService methods"
git commit -m "Wire ConversationAgent to LLMService.generate_response()"
```

**Commit message format:**
- **Subject line**: Capitalized, imperative mood, ≤50 chars
- **Body**: Explain *what* and *why*, not *how*

```
Wire DataIngestionAgent to real LLMService

Previously this agent returned placeholder data. Now it delegates
to LLMService.retrieve_context() to fetch real glucose readings,
events, and pattern summaries from the database.

This is part of Phase 1: Make the Chat Pipeline Real (PLAN.md).
```

### 3. Push and Create a Pull Request

```bash
# Push branch to remote
git push origin feat/wire-agent-coordinator

# Then create a PR on GitHub/GitLab
```

### 4. Review and Merge

```bash
# After PR is approved, merge to main
git checkout main
git pull origin main
git merge feat/wire-agent-coordinator
git push origin main

# Delete the branch (local + remote)
git branch -d feat/wire-agent-coordinator
git push origin --delete feat/wire-agent-coordinator
```

---

## Quick Reference Commands

### Everyday Workflow

```bash
# Start new work
git checkout main
git pull
git checkout -b feat/my-feature

# Commit progress
git add .
git commit -m "Descriptive commit message"

# Push and create PR
git push -u origin feat/my-feature

# After PR merges, clean up
git checkout main
git pull
git branch -d feat/my-feature
```

### Sync Branch with Main

```bash
# Option 1: Rebase (clean history)
git checkout feat/my-feature
git rebase main

# Option 2: Merge (preserves branch history)
git checkout feat/my-feature
git merge main
```

### Fix a Bug Fast

```bash
git checkout main
git checkout -b fix/stream-endpoint-crash
# ... fix the bug ...
git add .
git commit -m "Fix crash in chat/stream when coordinator unavailable"
git push -u origin fix/stream-endpoint-crash
# Create PR → merge → delete branch
```

---

## Recommended Initial Branches for T1D

Based on the code review, here's a prioritized list of branches to start with:

### Phase 1 (Now)

| Branch | What to Do |
|--------|------------|
| `refactor/consolidate-safety` | Merge SafetyAgent + SafetyScaffold into single source of truth |
| `perf/fix-n-plus-one-user-queries` | Change `lazy="selectin"` to `lazy="dynamic"` on large User relationships |
| `fix/encrypt-oauth-tokens` | Add encryption for Dexcom tokens in User model |

### Phase 2 (After above)

| Branch | What to Do |
|--------|------------|
| `refactor/normalize-timezones` | Add `DateTime(timezone=True)` consistently across all models |
| `feat/true-streaming-endpoint` | Implement real SSE token streaming from LLM |
| `refactor/reduce-context-duplication` | Remove redundant `_build_context()` in chat.py |

### Phase 3 (Ongoing)

| Branch | What to Do |
|--------|------------|
| `test/pattern-service-coverage` | Unit tests for all PatternService methods |
| `test/chat-pipeline-integration` | Integration tests for full chat flow |
| `docs/roadmap-update` | Update PLAN.md and SYSTEM.md with current progress |

---

## Why This Works for T1D

1. **Phase 1 matches GitHub Flow** — PLAN.md already defines phases as discrete units of work, which map perfectly to branches
2. **Low ceremony** — No `develop`, `release`, `hotfix` branches to manage. Just `main` + feature branches
3. **Safety through isolation** — Each change is tested in isolation before hitting `main`
4. **Reviewable** — PRs let you catch issues before they reach production (critical for a health app)
5. **Self-documenting** — Branch names + commit messages = changelog

---

## If You Want CI/CD Integration

Add a GitHub Actions workflow (`.github/workflows/ci.yml`):

```yaml
name: CI
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest --cov=app
      - run: ruff check app/
```

This would automatically run tests on every PR before you can merge to `main` — adding a safety net.

---

## Summary

```
main  ← protected — never commit directly here
  │
  └── feat/*      — new features
  └── fix/*       — bug fixes
  └── refactor/*  — code restructuring
  └── test/*      — test additions
  └── docs/*      — documentation
  └── chore/*     — maintenance
  └── perf/*      — performance
```

**Simple rule**: If you're about to type `git commit` on `main`, stop and create a branch first.