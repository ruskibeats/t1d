---
name: "reverse-engineer-ts-to-python-service"
description: "Reverse-engineer a TypeScript/JS project's API protocol and build a Python service equivalent. Use when an existing TypeScript project implements an API (like LibreLinkUp) but you need a Python implementation, Docker is unavailable, or you need to bypass a middleware."
version: 6
created: "2026-05-20"
updated: "2026-05-20"
---
# Reverse-Engineer TypeScript API → Python Service

## When to Use
- An existing TypeScript/Node.js project implements an API you need (e.g., LibreLinkUp client, Nightscout bridge)
- Docker is unavailable to run the existing containerized service
- You need a direct Python service instead of routing through a middleware (e.g., going direct to LibreLinkUp instead of LibreLinkUp → Nightscout → your app)
- The target API is undocumented and the TS project is your best spec

## Procedure
### 1. Locate the Target Project
- First, check if Docker is available (`docker info`) — if yes, consider running the existing containerized service directly
- If Docker is unavailable or you need to bypass a middleware, proceed with reverse engineering
- Search GitHub for relevant projects: `gh search repos "<description>" --limit 5` or browser search
- Check if your project already has a reference (docker-compose.yml with image name)
- Clone or download the source

### 2. Map the Auth Mechanism
- Check if the TS project uses a CookieJar/tough-cookie (cookie-based auth) or an Authorization header (Bearer/token auth)
- **Cookie-based auth**: Login returns `Set-Cookie` headers with session/auth tokens, not a JSON body with a token string. Subsequent requests must send these cookies. The cookies may be scoped to specific subdomains (region-specific).
- **Bearer/token auth**: Login returns a JSON response with a `token`/`access_token`/`authTicket` field. Subsequent requests add `Authorization: Bearer <token>` header.
- **Browser DevTools for cookie capture**: For cookie-based APIs, open the TS project's web UI or a real browser login, use DevTools Network tab to capture the full cookie exchange. Cookies may not appear in response body JSON — they're in the `Set-Cookie` response header. Look for patterns like `auth-token-{region}` in cookie names.

### 3. Identify API Regional Fragmentation
- Check if the TS project constructs base URLs dynamically based on a `region` parameter (e.g., `eu`, `us`, `au`, `ap`)
- Region affects: (a) base API URL, (b) cookie domain, (c) authentication endpoint
- Test each region against a known-working credential — wrong region produces silent failures (no auth cookies, "No auth-token cookies found" errors)
- The TS project's default region may not match your target user's account region; make region configurable
## Pitfalls
- **Cookie-based auth region mismatch**: If the API uses cookie-based auth (e.g., `auth-token-{region}` cookies in `Set-Cookie` headers), you MUST match the region to the user's account region. Wrong region → no cookies set → silent auth failure with "No auth-token cookies found" or 401 errors. The cookie domain is region-scoped (e.g., `eu.libreview.io` vs `us.libreview.io`).
- **Auth mechanism detection from TS source**: Check the TS project's HTTP client setup — `tough-cookie`/`CookieJar` references indicate cookie-based auth; `Authorization` header builders indicate Bearer/token auth. These require fundamentally different Python implementations (`httpx.Client(cookies=...)` with cookie jar vs `Authorization` header).
- **Browser cookie capture for auth debugging**: When the TS project's auth flow is unclear, use a real browser: (1) log in via the official web interface, (2) open DevTools → Application → Cookies, (3) examine cookie names, domains, and values. Compare against what your Python client is sending/receiving. This is especially important for cookie-based APIs where the cookie exchange is invisible in response bodies.
- **Don't assume Bearer token just because it's a modern API**: Many health APIs (LibreLinkUp, some CGM platforms) use cookie-based auth inherited from legacy session patterns, not OAuth2/Bearer token patterns.
## Verification
1. Run the test script with real credentials from .env
2. Verify: ✅ Login succeeds (200, returns auth ticket)
3. Verify: ✅ Connections endpoint returns patient data
4. Verify: ✅ Graph endpoint returns glucose readings
5. Verify: ✅ Data types match expected schema (timestamp, value, trend)
6. Verify: ✅ Service integrates with existing ingestion pipeline