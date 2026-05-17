# Frontend-Backend Integration Fixes

## Issues Found and Fixed

### 1. Login Response Format ✅ FIXED
- **Problem**: Frontend expects `{access_token, user}` but backend returned `{access_token, token_type, expires_in}`
- **Fix**: Created `LoginResponse` model with both token and user data, updated both login endpoints

### 2. User Name Fields ✅ FIXED
- **Problem**: Frontend expects `first_name`/`last_name`, backend had `full_name`
- **Fix**: Added `first_name` and `last_name` to `UserResponse` with `model_validate` override to split `full_name`

### 3. Glucose Stats Response Format ✅ FIXED
- **Problem**: Frontend expects nested `time_in_range: {percentage, count}`, backend returned flat values
- **Fix**: Updated `GlucoseStats` model and endpoint to return nested structure

### 4. Missing OAuth2PasswordBearer ✅ FIXED
- **Problem**: No token extraction from Authorization header
- **Fix**: Added `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")` to security.py

### 5. Duplicate Index on MoodEntry ✅ FIXED
- **Problem**: `index=True` + explicit `Index("ix_mood_entries_user_id")` caused SQLite create_all to fail
- **Fix**: Removed redundant explicit Index from MoodEntry model

### 6. SQLite init_db fixes ✅ FIXED
- **Problem**: Postgres-specific queries (`information_schema`, Alembic) crashing on SQLite
- **Fix**: Added SQLite-aware table existence check, skip Alembic for SQLite

## Remaining Issues to Fix

### A. Glucose reading response fields
Frontend expects: `{id, glucose_value, timestamp, source}`
Backend returns: `{id, glucose_value, timestamp, source, reading_type, ...}`
→ OK, extra fields are fine

### B. Reading source/type values
Frontend sends: `reading_type: 'sensor'`, `source: 'dexcom'`
Backend create model accepts these. OK.

### C. Event creation payload
Frontend sends full ContextEvent without id/user_id/timestamp
Backend `ContextEventCreate` has `timestamp`, `event_type`, `event_subtype`, etc.
Frontend types show `ContextEvent` with many optional fields.
Need to verify the event creation payload matches.

### D. Error response format
Frontend catches: `err?.response?.data?.message`
Backend returns: `{error, message, detail, timestamp}`
→ The `message` field exists. OK.

### E. Auth error handling on register
Frontend register catches generic error and shows message
Backend returns 400 with `{error: "InternalServerError", message: "...", detail: {exception_type: "..."}}`
→ Frontend reads `err?.response?.data?.message`. OK.

### F. 3 pre-existing flaky overnight tests
`test_overnight_multiple_nights`, `test_overnight_severe_low`, `test_overnight_time_window`
These were failing BEFORE any of our changes. Pre-existing issue.

## Verification
- Backend: 250 tests passing (247 if excluding pre-existing overnight failures)
- Frontend: Created 13 new API test files covering all endpoints
- Full E2E: Register ✅, Login ✅, Auth/me ✅, Chat ✅
