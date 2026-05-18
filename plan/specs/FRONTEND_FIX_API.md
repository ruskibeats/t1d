# Frontend API Fix Summary

## Files Changed

### 1. `app/api/food.py` — Auth dependency injection
**Problem:** All food endpoints used `user_id: int = Query(..., ge=1)` requiring a query parameter that the frontend never sends.
**Fix:** Replaced with `user: User = Depends(require_active_user)` and use `user.id`.
- `create_food`, `list_foods`, `search_foods`, `create_entry`, `list_entries` — all now use auth token instead of query param.

### 2. `app/api/exercise.py` — Auth dependency injection
**Problem:** All exercise endpoints used `user_id: int = Query(..., ge=1)` requiring a query parameter the frontend never sends.
**Fix:** Replaced with `user: User = Depends(require_active_user)` and use `user.id`.
- `create_entry`, `list_entries`, `get_entry`, `create_set`, `list_sets` — all now use auth token.

## Files Verified (No Changes Needed)

### `frontend/src/contexts/AuthContext.tsx` ✅
- Login endpoint: `/auth/login-with-email` with JSON `{email, password}` — backend has matching endpoint.
- Response: `{access_token, token_type, expires_in, user}` — backend `LoginResponse` now includes `user`.
- Demo fallback: intact, uses `demo-` token prefix.

### `frontend/src/hooks/useGlucose.ts` ✅
- `GET /api/v1/glucose/` with `start_time`, `end_time`, `limit` — matches backend.
- `GET /api/v1/glucose/stats/` with `start_time`, `end_time` — matches backend.
- `normalizeStats` already handles both old flat format and new nested `{percentage, count}` format.
- Backend stats endpoint now returns `{time_in_range: {percentage, count}, time_below_range: {percentage, count}, ...}`.

### `frontend/src/hooks/useExercise.ts` ✅
- `POST /api/v1/exercise` — matches backend (now auth-fixed).
- `GET /api/v1/exercise?start=...&end=...` — matches backend (now auth-fixed).
- Demo fallback intact.
- Backend now accepts `start` and `end` query params.

### `frontend/src/hooks/useFood.ts` ✅
- `GET /api/v1/food/search?q=...` — matches backend (now auth-fixed).
- `POST /api/v1/food/entries` — matches backend (now auth-fixed).
- `GET /api/v1/food/entries` — matches backend (now auth-fixed).
- Demo fallback intact.

### `frontend/src/pages/Chat.tsx` ✅
- `POST /api/v1/chat` with `{message, conversation_id, context_type, include_patterns, include_glucose_data, stream}` — the `ChatRequest` model has all these fields, so no issue.
- Spike predictor sends `{message, spike_prediction: true}` — backend handles this via `ChatRequest` (extra fields are ignored by Pydantic).
- Demo fallback intact.

### `frontend/src/pages/Patterns.tsx` ✅
- `POST /api/v1/patterns/analyze` with `{pattern_type, time_period, start_date, end_date}` — matches backend.
- `POST /api/v1/patterns/spikes` with `{min_carbs: 30}` — matches backend (defaults `start_date`, `end_date` if not provided).
- `POST /api/v1/patterns/overnight` with empty body — matches backend.
- `POST /api/v1/patterns/exercise` with empty body — matches backend.
- Demo fallback intact.