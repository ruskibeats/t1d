---
name: "fix-sqlalchemy-pending-rollback-loop"
description: "Fix PendingRollbackError cascade in FastAPI/SQLAlchemy async services where an unhandled SQLAlchemy exception leaves the session in a broken state, causing all subsequent requests to fail with PendingRollbackError. Add explicit rollback() in exception handlers and prefer transaction context managers."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Fix PendingRollbackError Loop in FastAPI/SQLAlchemy Async Services

## When to Use

- A FastAPI endpoint suddenly returns HTTP 500 with `sqlalchemy.exc.PendingRollbackError` for ALL subsequent requests
- The error stack trace shows `This Session's transaction has been rolled back by a nested rollback() call. To begin a new transaction, issue Session.rollback()` or similar
- The error started after a SQLAlchemy exception (IntegrityError, ProgrammingError, DataError) in a service method
- No explicit `rollback()` call exists in the service method that raised the original exception

**Boundary**: This is about broken session state in async SQLAlchemy services. For Alembic migration errors, use the fix-alembic-* skills. For SQLAlchemy connection pool issues, this is not the right skill.

## Procedure

### 1. Confirm the PendingRollbackError loop

Check the application logs for:
- `sqlalchemy.exc.PendingRollbackError` in recent requests
- Preceding errors from the SAME session like `IntegrityError`, `ProgrammingError`, or `DataError`
- Every subsequent request to the same or related endpoints failing with the same PendingRollbackError

The chain of events is:
1. Service method A executes a SQL statement that raises SQLAlchemyError
2. The exception is caught by FastAPI, but the session is NOT rolled back
3. The session enters a "pending rollback" state
4. Next request hits the same endpoint → reuses session → PendingRollbackError
5. All subsequent requests cascade-fail until the session is replaced or manually rolled back

### 2. Identify the root cause service method

Search for the first error that triggered the cascade:

```bash
# Look for the original IntegrityError/ProgrammingError, not the PendingRollbackError
grep -n "IntegrityError\|ProgrammingError\|DataError\|SQLAlchemyError" app/api/*.py app/*/service.py
```

Common triggers:
- INSERT of a duplicate key (unique constraint violation)
- UPDATE with invalid data type
- Foreign key violation
- NOT NULL constraint failure
- PostgreSQL ENUM value not in the type definition

### 3. Add explicit rollback to the service method

The fix is to wrap the operation in a try/except that rolls back the session on error:

```python
# Before (broken - leaves session in pending rollback):
async def create_entry(self, user_id: int, data: dict) -> dict:
    entry = EntryModel(user_id=user_id, **data)
    self.db.add(entry)
    await self.db.commit()
    return {"id": entry.id}

# After (fixed - rolls back on error):
async def create_entry(self, user_id: int, data: dict) -> dict:
    try:
        entry = EntryModel(user_id=user_id, **data)
        self.db.add(entry)
        await self.db.commit()
        return {"id": entry.id}
    except SQLAlchemyError:
        await self.db.rollback()
        raise  # Re-raise so FastAPI handler can return appropriate error
```

### 4. Alternative: Use a transaction context manager

For methods with multiple steps, prefer an explicit transaction:

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def bulk_operation(self, items: list) -> dict:
    try:
        async with self.db.begin() as tx:
            for item in items:
                self.db.add(EntryModel(**item))
        # Auto-committed on success, auto-rolled back on error
        return {"created": len(items)}
    except SQLAlchemyError:
        # Session is already rolled back by the context manager
        raise
```

Note: `async with self.db.begin()` automatically calls `rollback()` on the outer session when an exception occurs INSIDE the block. If a subsequent operation outside the block uses the same session, it works fine.

### 5. Or: Use a database-level exception handler in the API layer

If the service method is called from an API handler, add exception handling there too:

```python
@router.post("/entries")
async def create_entry(
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    try:
        result = await entry_service.create_entry(current_user.id, data.dict())
        return result
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate entry")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error")
```

### 6. Add defensive rollback in the dependency

To prevent this issue entirely, add defensive rollback in the session dependency:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

This pattern ensures the session is always rolled back and closed, even on unhandled exceptions.

## Pitfalls

- **Rollback does NOT reset autocommit mode**: If the session has autocommit disabled (the default for async sessions), you must explicitly call `rollback()` after an error. The session won't auto-recover.
- **Nested rollbacks**: Avoid calling `rollback()` when the session is already clean. A rollback on a clean session is harmless but calling an operation after a failed flush without rollback is not.
- **Session reuse across requests**: Async session per-request (common in FastAPI) means the broken session is discarded after the request. But if using middleware or global session, pending rollback will cascade to all subsequent requests.
- **FastAPI dependency + Depends pattern**: If `get_db` is a generator (async generator function), FastAPI wraps it in context management. If the service method fails and doesn't rollback, the `get_db` cleanup code should still handle rollback in its `finally` block.
- **Unit test cleanup**: In pytest, make sure `db.close()` and `db.rollback()` are called in test teardown, or use `event_loop` and `connection` fixtures that auto-rollback.
- **Multiple services sharing session**: If multiple services share the same session object (e.g., passed through as a dependency), any one of them leaving the session in a pending rollback state breaks all others.
- **`async with session.begin()` vs `await session.commit()`**: `async with session.begin()` auto-rolls back and can be safer. `await session.commit()` requires explicit error handling. Prefer `async with` for multi-step operations.

## Verification

1. Reproduce the failing request that originally caused the error
2. Confirm it returns a proper error response (400/409/422) not PendingRollbackError
3. Make 3-5 subsequent requests to the SAME endpoint — they should succeed
4. Make requests to OTHER endpoints using the same session — they should also succeed
5. Check application logs for PendingRollbackError — should be zero after the fix
6. For the defensive dependency fix: inject a deliberate error and verify no PendingRollbackError leaks to subsequent requests