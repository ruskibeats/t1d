---
name: fastapi-endpoint-security-audit
description: "Audit all FastAPI endpoint files for security gaps: missing authentication, missing input validation, weak error handling, and missing rate limiting. Scans router decorators to identify endpoints and checks for auth dependencies, pydantic constraints, and exception safety. Use when securing a FastAPI codebase, performing a security review, or hardening API endpoints."
version: 1
created: 2026-05-19
updated: 2026-05-19
---
# FastAPI Endpoint Security Audit

## When to Use

Use this skill when performing a security audit of a FastAPI codebase. It provides a methodology for systematically scanning all API endpoint files, categorizing vulnerabilities by severity, and generating actionable findings.

**Trigger phrases**: "security audit fastapi", "check api endpoints for auth", "find unauthenticated endpoints", "audit fastapi security", "review api validation", "scan api for vulnerabilities", "api hardening review"

**Pre-requisites**:
- Access to the FastAPI source code in `app/api/` or similar directory
- Understanding of FastAPI patterns (router, Depends, query params, path params)

## Procedure

### Step 1: Discover all API endpoint files

First, find all files that define FastAPI routers:

```bash
# Find all router files
ls app/api/
# Or for nested structures:
find app/api/ -name '*.py' | sort
```

### Step 2: Count endpoints per file and find auth patterns

For each endpoint file, count the total endpoints and determine whether auth is applied:

```bash
# Count total route decorators (endpoints)
grep -n 'router\.\(get\|post\|put\|delete\|patch\)(' app/api/**.py

# Identify auth pattern — is it applied via dependency injection?
grep -rn 'Depends' app/api/**.py | grep -v 'Depends()' | grep -i 'auth\|user\|token\|session\|current'

# Check for middleware-level auth
grep -rn 'middleware\|Middleware' app/api/**.py
grep -rn 'add_middleware' app/main.py app/core/**.py
```

**Key insight**: Look for whether auth is per-endpoint (`Depends(get_current_user)`) or middleware-based. In a per-endpoint setup, endpoints without a `Depends(get_current_user)` parameter are **unauthenticated**.

### Step 3: Find endpoints with a `user_id` query parameter instead of auth

A common anti-pattern: endpoints accept `user_id` as a query parameter without authentication, which lets any caller impersonate any user:

```bash
# Find endpoints with user_id as a query param (likely unauthenticated)
grep -rn 'user_id:' app/api/**.py | grep -v 'path\|route\|response'
```

### Step 4: Categorize by severity

For each file found in Steps 2-3, categorize:

| Severity | Label | Criteria |
|----------|-------|----------|
| **P0 — Critical** | `no-auth` | Endpoint accepts `user_id` as query param but has zero auth checks. Any caller can access/modify any user's data. |
| **P1 — High** | `no-validation` | No `ge`/`le`/`min_length`/`max_length` constraints on query params. No format validation on ISO dates. |
| **P2 — Medium** | `bad-error-handling` | `except Exception` returning `str(e)`, unhandled `ValueError` from `datetime.fromisoformat()`, no limits on aggregation queries. |
| **P3 — Low** | `missing-guardrails` | No rate limiting on auth-sensitive endpoints (login, register), missing webhook signature verification, placeholder endpoints always returning success. |

### Step 5: Deep-dive each category

#### P0 — Missing Authentication

For each unauth'd file, enumerate specific endpoints:

```bash
# List all endpoints in a file with their route and method
grep -n 'router\.\(get\|post\|put\|delete\|patch\)(' app/api/fasting.py
```

Examine each endpoint's function signature for `Depends()` calls:

```bash
# Show function signatures to check for auth dependency
grep -A1 'def ' app/api/some_file.py | grep -v '^--$'
```

Document findings as a table with: File, Endpoints count, Issue description.

#### P1 — Missing Input Validation

Check for these patterns:

```bash
# No ge/le constraints on numeric params — grep for parameters with : int but no Ge/Le
grep -n 'limit:\|offset:\|skip:\|window_minutes:' app/api/**.py | grep -v 'Ge\|Le\|Field'

# Missing max_length on string params
grep -n 'str =' app/api/**.py | grep -v 'max_length\|Path('

# Missing min_length on search queries
grep -n 'q:\|query:\|search:' app/api/**.py | grep -v 'min_length\|max_length'

# Raw datetime.fromisoformat without validation
grep -rn 'fromisoformat' app/api/**.py
```

#### P2 — Weak Error Handling

```bash
# Bare except Exception returning str(e) — leaks internal details
grep -n 'except.*:' app/api/**.py | grep -v 'HTTPException\|ValidationError\|pass\|log\|logger' | head -30

# No limit on aggregation queries (OOM risk)
grep -rn '\.all()\|fetchall' app/api/**.py | grep -v 'limit\|offset'
```

#### P3 — Missing Guardrails

```bash
# Check for rate limiting
grep -rn 'limiter\|rate_limit\|throttle\|slowapi' app/**.py

# Check for webhook signature verification
grep -rn 'signature\|verify\|secret\|webhook' app/api/*webhook*.py app/api/garmin*.py app/api/withings*.py

# Check placeholder auth endpoints
grep -rn 'verify-email\|reset-password\|forgot-password' app/api/**.py
```

### Step 6: Calculate security score

| Score | Criteria |
|-------|----------|
| 🔴 **Critical** (0–20%) | Any P0 finding (unauth'd endpoints with user_id) |
| 🟠 **Poor** (20–40%) | P0 found without user_id, or >50% endpoints unauth'd |
| 🟡 **Fair** (40–60%) | All endpoints have auth but P1/P2 findings exist |
| 🟢 **Good** (60–80%) | Only P3 findings remain |
| ✅ **Excellent** (80–100%) | No findings |

### Step 7: Generate actionable findings

Create a structured report with these sections:

1. **Executive Summary**: Overall security score and key findings
2. **Critical (P0)** — Authentication gaps: File-by-file breakdown with endpoint count
3. **High (P1)** — Input validation gaps: Numeric constraints, string limits, date parsing
4. **Medium (P2)** — Error handling gaps: Exception leaks, OOM risks
5. **Low (P3)** — Missing guardrails: Rate limiting, webhook verification, placeholder endpoints
6. **Action items**: Convert each finding into a tracked task with priority label

For each finding:
- File path and line number
- Short description of the vulnerability
- The specific pattern that needs fixing
- Priority label (P0/P1/P2/P3)

## Pitfalls

### User_id query param is a false sense of security

If an endpoint accepts `user_id: int` as a query parameter but has **no authentication dependency**, any caller can query any user's data just by guessing IDs. This is the most common P0 vulnerability in FastAPI apps that use per-endpoint auth patterns.

**Prevention**: Auth must verify that `user_id` matches the authenticated user's ID, or that the caller has admin privileges.

### Middleware auth can be overlooked

Some endpoints rely on middleware for auth (e.g., `TrustedHostMiddleware`), but this only checks the host header — it does NOT provide user identity. Verify that middleware auth actually validates tokens/sessions, not just origin.

### Router prefix doesn't mean auth

A file like `app/api/auth.py` might define endpoints like `POST /auth/login` — these endpoints deliberately have no auth dependency (you can't be logged in before you log in). These are NOT vulnerabilities. Only flag endpoints that expose user-specific data without auth.

### Bare Exception catches leak stack traces

`except Exception as e: raise HTTPException(400, detail=str(e))` returns internal error messages to the client. This can leak SQL query details, file paths, and schema structure. Flag these as P2.

### "Limit" is not a security measure

Some endpoints pass `limit=1000` as a default but never enforce it against large requests. Check whether `limit` is actually used in the SQL query, not just accepted as a parameter.

## Verification

After completing the audit, verify:

- [ ] Every endpoint file has been scanned
- [ ] Each endpoint is categorized as auth'd or unauth'd
- [ ] P0 findings include specific file paths and line numbers
- [ ] P0 findings distinguish between "deliberately unauth'd" (login) and "missing auth" (data endpoints)
- [ ] Input validation gaps are documented with specific missing constraints
- [ ] Error handling gaps reference specific exception patterns
- [ ] Rate limiting is checked on at least: login, register, forgot-password
- [ ] Webhook signature verification is checked on all webhook endpoints
- [ ] Action items are tracked with priority labels (P0/P1/P2/P3)