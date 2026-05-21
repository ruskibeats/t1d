# Clanker Ops Plan — #164: LibreLinkUp Direct API Integration

## Intended Outcome
Direct LibreLinkUp API service that connects to Abbott's LibreView API, bypassing Nightscout for local development. Fully wired into the T1D Companion sync pipeline with API endpoints.

## Step-by-Step
1. Research LibreLinkUp API (reverse-engineered from LibreLinkUp iOS app)
2. Create `app/services/librelinkup_service.py` with login, graph fetch, patient lookup, sync
3. Add LibreLinkUp fields to `app/db/models.py` User model
4. Add LibreLinkUp Pydantic models to `app/models/user.py`
5. Add LibreLinkUp sync handler to `app/services/sync_service.py`
6. Add LibreLinkUp API endpoints to `app/api/cgm.py` and `app/api/users.py`
7. Add LibreLinkUp to `app/api/providers.py`
8. Create test script `scripts/test_librelinkup.py`
9. Verify live data from user Tom Batchelor

## Verification
- ✅ Login to LibreView API works (Tom Batchelor account, EU2 region)
- ✅ Patient connection found (d11c0acc-754b-11ed-9da8-0242ac110005)
- ✅ Glucose readings fetched: 47 readings, 60-223 mg/dL range
- ✅ Timestamp parsing fixed (US format: M/D/YYYY H:MM:SS AM/PM)
- ✅ All API endpoints register (verified with import tests)
- ✅ Sync pipeline includes librelinkup as a recognized source

## Dependencies
- `app/services/librelinkup_service.py` (new)
- `app/db/models.py` (modified)
- `app/models/user.py` (modified)
- `app/services/sync_service.py` (modified)
- `app/api/cgm.py` (modified)
- `app/api/users.py` (modified)
- `app/api/providers.py` (modified)

## Audit
- Created: 2026-05-20
- Assigned: @pi
- Status: completed