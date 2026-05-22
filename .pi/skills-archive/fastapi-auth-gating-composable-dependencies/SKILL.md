---
name: "fastapi-auth-gating-composable-dependencies"
description: "Implement FastAPI route protection with composable dependency injection. Layer JWT auth into get_current_user → require_active_user → require_verified_email, where each wrapper adds one constraint and passes the User object through. Use when building or reviewing a FastAPI app that needs tiered route access (authenticated / active / verified), or when code review asks to \"add auth gating\" to existing routes."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

Implement FastAPI authentication gating with composable dependency injection. Use when protecting API routes with JWT-based auth and you need layered access levels (authenticated → active → verified email). Also use when code review asks you to "add auth gating" to existing routes — the composable wrapper pattern makes it trivial to add with a single `Depends()` parameter per route.

**Trigger phrases**: "add auth gating", "protect routes with auth", "require active user", "FastAPI dependency chain", "JWT authentication FastAPI", "gate endpoint behind auth", "belt-and-suspenders auth"

**Not for**: Setting up JWT token creation, password hashing, or OAuth2 flows. This skill assumes JWT decode/auth infrastructure already exists (`decode_token`, `get_user_by_id`, etc.).

## Procedure

### 1. Define the Base Dependency (`get_current_user`)

Create the primary dependency that extracts and validates the JWT, fetches the user from the database, and performs the initial active check. This is the only dependency that talks to external services.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    session: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # 1. Decode JWT
    try:
        token_data = decode_token(token)
        user_id = int(token_data.sub)
    except (JWTError, ValueError):
        raise credentials_exception

    # 2. Fetch user from DB
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise credentials_exception

    # 3. Belt-and-suspenders: check is_active at the earliest point
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user
```

### 2. Create Composable Wrapper Dependencies

Each wrapper is a thin, single-responsibility pass-through that adds one constraint. They chain from each other in strict order.

```python
async def require_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Ensure user is active. Thin wrapper for belt-and-suspenders coverage."""
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return user


async def require_verified_email(
    user: User = Depends(require_active_user),
) -> User:
    """Ensure user has verified email. Chains from require_active_user, not get_current_user."""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return user
```

**Key design principles**:
- Each wrapper chains from the previous (`require_verified_email` chains from `require_active_user`, not from `get_current_user` directly) — this ensures all prior checks pass
- Each wrapper returns the `User` object (pass-through), so route handlers can access `user.id`, `user.email`, etc.
- Each wrapper handles exactly one concern (single-responsibility)
- The active check in `get_current_user` and `require_active_user` is intentional belt-and-suspenders — if someone later removes the active check from `get_current_user` (e.g., thinking "getter shouldn't enforce policy"), routes using `require_active_user` remain protected

### 3. Wire Dependencies into Routes

Add the appropriate dependency to each route handler. Routes pick the minimum access level they need.

```python
# ── Public endpoint (no auth required) ──
@router.get("/anchors", summary="List all anchors (public)")
async def list_anchors() -> list[dict[str, Any]]:
    ...

# ── Authenticated-only endpoint ──
@router.get("/runs", summary="List simulation runs")
async def list_sim_runs(
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> SimRunListResponse:
    ...

# ── Mutating endpoint ──
@router.post("/runs/{run_id}/start", summary="Start a simulation run")
async def start_sim_run(
    run_id: int,
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> SimRunResponse:
    ...
```

### 4. Add Auth Gating to Existing Routes (Migration Pattern)

When adding auth to routes that previously had no auth:

1. Add `user: User = Depends(require_active_user)` as a new parameter
2. FastAPI injects it via DI automatically — no other code changes needed
3. The parameter can be unused (just for gating) or used for owner checks

```python
# Before
@router.get("/runs/{run_id}/evaluation")
async def get_evaluation(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> EvaluationSummary:

# After (add one line)
@router.get("/runs/{run_id}/evaluation")
async def get_evaluation(
    run_id: int,
    user: User = Depends(require_active_user),  # <-- one-line addition
    db: AsyncSession = Depends(get_db),
) -> EvaluationSummary:
```

### 5. Handling the Public-Facing Exception

The `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")` means FastAPI automatically returns a 403 with "Not authenticated" for endpoints that require `get_current_user` when no token is provided. This is fine for most cases but can be customized if you need a different response format.

## Pitfalls

- **401 vs 400 vs 403 is meaningful**: Use 401 for invalid/missing credentials (includes `WWW-Authenticate` header), 400 for resource-level issues like inactive user, 403 for permission-level issues like unverified email. Clients and middleware (e.g., refresh-token interceptors) rely on these distinctions.

- **Don't put the `Depends(get_db)` after the auth dep**: While FastAPI resolves deps in any order, convention places DB-acquiring deps before auth deps for clarity. The pattern `db: AsyncSession = Depends(get_db)` before `user: User = Depends(...)` is idiomatic.

- **Async DB queries require `await` in async def dependencies**: If using async SQLAlchemy with asyncpg, every DB operation in `get_current_user` must be `await`ed. Using `def` instead of `async def` will crash with a missing greenlet error.

- **Active check duplication is intentional**: `get_current_user` checks `is_active`. `require_active_user` re-checks it. This is not a bug — it's a defense against future refactors where someone removes the policy check from the "getter" dependency.

- **The user object is always available**: Since wrappers pass through the `User` object, handlers can always access `user.id`, `user.email`, etc. without needing a separate DB lookup.

- **Token extraction does NOT trigger on every call**: `OAuth2PasswordBearer` only extracts the token; the actual validation (DB lookup, active check) happens in `get_current_user`. If validation fails, the route is rejected before any handler logic runs.

## Verification

1. **Public endpoint**: Call without Authorization header → expect 200 (no auth required)
2. **No token**: Call protected endpoint without header → expect 403 with "Not authenticated"
3. **Invalid token**: Call with `Authorization: Bearer invalid-token` → expect 401 with "Could not validate credentials"
4. **Inactive user**: Call with valid token for deactivated user account → expect 400 with "Inactive user"
5. **Unverified email**: Call endpoint using `require_verified_email` with valid but unverified user → expect 403
6. **Active user**: Call protected endpoint with valid token for active user → expect 200
7. **User propagation**: Verify handler code can access `user.id` from the injected dependency
8. **Code review**: Check that routes intended to be public explicitly omit the auth `Depends()` parameter