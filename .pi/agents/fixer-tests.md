# Fixer — Test Infrastructure

## Task
Fix test infrastructure issues to make the test suite reliable, fast, and CI-ready.

## Scope
1. **`tests/conftest.py`** — refine table creation strategy. The current approach creates only core tables. Either:
   - Document the subset limitation clearly, OR
   - Fix the duplicate index problem in the domain models that blocks full `Base.metadata.create_all()` on SQLite.
2. **`tests/__init__.py`** — verify the JSONB/ENUM compat patch still works after any conftest changes.
3. **`app/core/logging_config.py:84`** — replace `datetime.utcnow().isoformat()` with `datetime.now(timezone.utc).isoformat()`.
4. **Ensure `pytest -x --tb=short` passes in <5 seconds** for the focused test suite.
5. **Run full suite and count warnings** — goal is <100 warnings (down from ~452).

## Verification
```bash
python3 -m pytest tests/ai/test_safety.py tests/test_llm_service.py tests/test_chat_pipeline.py tests/test_pattern_service.py -q 2>&1 | grep -c warning
python3 -m pytest tests/ai/test_safety.py tests/test_llm_service.py tests/test_chat_pipeline.py tests/test_pattern_service.py -x --tb=short
time python3 -m pytest tests/ai/test_safety.py tests/test_llm_service.py tests/test_chat_pipeline.py tests/test_pattern_service.py -q
```

## Output
- Updated files with fixes
- Brief summary of what was changed and warning count before/after
