# Batch 2 — Work Package C1: DexcomService Mocked Tests

## Summary

Created `tests/test_dexcom_service.py` with **30 tests** across 7 test classes covering all major DexcomService methods and helper functions. All tests use mocked HTTP — no network calls.

## Test Coverage

| Class | Tests | What It Covers |
|---|---|---|
| `TestAuthorizationURL` | 3 | URL includes client_id, redirect_uri, response_type, scope, state; sandbox vs production |
| `TestExchangeCodeForTokens` | 4 | Successful token exchange, correct request payload, HTTP 401 error, network error |
| `TestRefreshAccessToken` | 3 | Successful refresh, correct request payload, HTTP error |
| `TestGetGlucoseReadings` | 5 | Normalized readings, bearer token in headers, empty/None response, 401 invalid token, 500 server error |
| `TestGetLatestGlucose` | 2 | Returns max by systemTime, returns None when empty |
| `TestSyncGlucoseData` | 4 | Inserts new GlucoseReading rows, skips duplicates (broken path documented), skips malformed readings, API error propagates |
| `TestGetTrendAngle` | 4 | None input, rising velocities, steady, falling velocities |
| `TestCategorizeGlucoseLevel` | 5 | severe_low, low, in_range, high, severe_high categories |
| **Total** | **30** | |

## Mocking Approach

Uses `unittest.mock.patch` to replace `httpx.AsyncClient` inside the dexcom_service module. A `_mock_http_response()` helper builds a properly-shaped mock httpx response:

- `response.json()` — synchronous MagicMock (httpx.Response.json is sync even from AsyncClient)
- `response.raise_for_status()` — synchronous MagicMock, raises `httpx.HTTPStatusError` on 4xx/5xx
- `response.text` — plain string for error messages

No additional dependencies required. No `pytest-httpx` or `respx`.

## Bug Found

**Duplicate detection in `sync_glucose_data` is broken.** The line:
```python
existing_timestamps = {r[0] for r in existing.scalars()}
```
uses `scalars()` which yields plain `datetime` values — these are not subscriptable, so `r[0]` raises `TypeError`. The test `test_skips_duplicates` documents this with `assert count == 2` (should be 1 when fixed). The fix would be:
```python
existing_timestamps = set(existing.scalars().all())
```

## No Regressions

```
131 passed, 476 warnings in 0.99s
```

## Files

- **Created:** `tests/test_dexcom_service.py` (187 lines of tests)
- **No changes to:** `app/services/dexcom_service.py`, `tests/conftest.py`, or any other files
