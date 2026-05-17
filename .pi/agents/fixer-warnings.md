# Fixer — Warning Cleanup Sprint

## Task
Silence the Pydantic V2 deprecation warnings across the codebase. Target: <50 warnings in `pytest -q`.

## Scope
1. **All `app/*/schemas.py` files** — replace `class Config:` with `model_config = ConfigDict(...)`:
   ```python
   # Old
   class Config:
       from_attributes = True
   
   # New  
   model_config = ConfigDict(from_attributes=True)
   ```
   Files to check:
   - `app/measurements/schemas.py`
   - `app/fasting/schemas.py`
   - `app/mood/schemas.py`
   - `app/config.py`
   - `app/core/security.py`
   - `app/core/errors.py`
   - `app/sleep/schemas.py`
   - `app/water/schemas.py`
   - Any others `rg "class Config"` finds

2. **`app/db/base.py`** — replace `declarative_base()` import:
   ```python
   # Old
   from sqlalchemy.ext.declarative import declarative_base
   
   # New
   from sqlalchemy.orm import DeclarativeBase
   
   class Base(DeclarativeBase):
       pass
   ```
   (Check existing import first — it may already be `from sqlalchemy.orm`)

3. **`app/core/logging_config.py:84`** — `datetime.utcnow().isoformat()` → `datetime.now(timezone.utc).isoformat()`

4. **Verify no remaining `datetime.utcnow()`** in `app/` that isn't in a database model default.

## Verification
```bash
# Before count
python3 -m pytest tests/ai/test_safety.py tests/test_llm_service.py tests/test_chat_pipeline.py tests/test_pattern_service.py -q 2>&1 | grep "warning" | wc -l

# After count  
python3 -m pytest tests/ai/test_safety.py tests/test_llm_service.py tests/test_chat_pipeline.py tests/test_pattern_service.py -q 2>&1 | grep "warning" | wc -l

# All tests still pass
python3 -m pytest tests/ai/test_safety.py tests/test_llm_service.py tests/test_chat_pipeline.py tests/test_pattern_service.py -x --tb=short
```

## Output
- Updated files
- Warning count before/after
