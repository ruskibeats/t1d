---
name: "t1d-cgm-provider-integration"
description: "Add a new CGM data provider to the T1D Companion sync pipeline. Covers creating the service class (auth, data fetching, parsing), adding DB models/fields, wiring into sync_service.py, adding API endpoints (connect/disconnect/test/sync), and verifying with live data. Use when integrating a new CGM source like LibreLinkUp, direct Dexcom API, or Medtronic CareLink."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
# Add a New CGM Provider to the T1D Sync Pipeline

## When to Use
- Adding a new CGM data source (e.g., LibreLinkUp, direct Dexcom API, Medtronic CareLink)
- Replacing a proxy/gateway (e.g., bypassing Nightscout for local dev)
- The provider has a REST API with auth and batch data fetching (not OAuth wearable sensors)
- The provider needs connect/disconnect/test/sync lifecycle management

Do NOT use for:
- OAuth wearable providers (Fitbit, Garmin, etc.) — use `wearable-ingestion-provider-add` skill instead
- Read-only data sources without user authentication
- Database-level changes only (use appropriate model/DB skills)

## Procedure

### 1. Research API Protocol
- Investigate the provider's API: endpoints, auth mechanism, data format
- For undocumented APIs, examine mobile app traffic or community documentation
- Note region-specific endpoints (many health APIs vary by region)
- Identify: auth flow, glucose reading structure, timestamp format, pagination

### 2. Create Service Class (`app/services/{provider}_service.py`)
- Define Pydantic models for: config, auth ticket, glucose reading, API response
- Implement `_build_headers()` with User-Agent spoofing (health APIs often check)
- Implement auth: login endpoint, token storage, header construction
- Implement data fetching: `get_glucose_readings()` returning parsed readings
- Handle timestamp normalization — many health APIs use US format (`M/D/YYYY H:MM:SS AM/PM`)
- Use `httpx.AsyncClient` with cookie jar for stateful sessions
- Define region-to-endpoint mapping dict
- Add proper error handling and logging

### 3. Add DB Models/Fields (`app/db/models.py`)
- Add provider-specific connection fields to the User model:
  - `{provider}_email`, `{provider}_password` (encrypted)
  - `{provider}_region`, `{provider}_version`
  - `{provider}_patient_id`, `{provider}_last_sync`
  - `{provider}_connected` flag
- Add CGM source type to `GlucoseReading` if needed:
  - `cgm_source` field: `"nightscout"`, `"dexcom"`, `"librelinkup"`, etc.

### 4. Add Pydantic Models (`app/models/user.py`)
- Connection detail model (inheriting from ProviderConnectionDetail)
- Connect request/response schemas
- Disconnect response schema
- Test result schema
- Ensure all new types are exported

### 5. Wire into Sync Service (`app/services/sync_service.py`)
- Add the provider as a recognized sync source
- In `trigger_manual_sync()` or equivalent, add a branch for the new provider
- Handle source type routing: distinguish between Nightscout, Dexcom, LibreLinkUp, etc.
- Rate limiting and error handling

### 6. Add API Endpoints (`app/api/cgm.py` and/or `app/api/users.py`)
- `POST /{provider}/connect` — authenticate and store credentials
- `POST /{provider}/disconnect` — clear stored credentials
- `POST /{provider}/test` — test connection without saving
- `GET /{provider}/sync` — trigger manual sync
- `GET /providers` — list connected providers
- Use `require_active_user` dependency for auth on all endpoints
- Add proper Pydantic response models

### 7. Register Provider (`app/api/providers.py`)
- Add to the provider list so frontend can discover available connections
- Include status indicator (connected/disconnected)

### 8. Create Test Script (`scripts/test_{provider}.py`)
- Import the service class and test config
- Login → verify patient connection → fetch readings → display summary
- Helpful for manual verification during development
- Handle missing .env config gracefully

### 9. Verify with Live Data
- Run the test script with a real account
- Verify: auth works, readings are fetched, timestamps parse correctly, range looks realistic
- Verify API endpoints register (import test)
- Verify sync pipeline includes the new source

## Pitfalls

- **Timestamp format**: Many health APIs return US format `M/D/YYYY H:MM:SS AM/PM`. Try ISO 8601 first, fall back to US format with `strptime`. Always handle both.
- **Region-specific endpoints**: Health APIs often have per-region subdomains. Map them exactly; don't guess a default.
- **Password hashing**: Some APIs require password hashing (e.g., SHA-256) in auth headers, not the raw password. Check the protocol.
- **User-Agent spoofing**: Health APIs may reject non-mobile User-Agents. Use a realistic iPhone/Safari UA.
- **Cookie management**: Use `httpx.AsyncClient` with a cookie jar to maintain session state across requests.
- **Auth ticket expiry**: Check `expires` field in auth response. Re-auth on 401.
- **Source type routing**: When wiring into sync_service, distinguish the new provider from existing ones using the `cgm_source` field — don't just append to a single list.
- **.env configuration**: Add provider fields to .env.example and reference them in test scripts with graceful fallback.

## Verification

- `python3 -c "from app.services.{provider}_service import {Provider}Service; print('OK')"` — imports without error
- Provider test script runs and returns real glucose readings
- `POST /{provider}/connect` returns success for valid credentials
- `POST /{provider}/disconnect` clears stored credentials
- `GET /{provider}/sync` triggers sync and returns recent readings
- All existing tests still pass with `pytest -q`
- Manual check: readings have realistic values and correct timestamps