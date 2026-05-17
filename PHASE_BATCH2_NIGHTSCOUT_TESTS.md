# Batch 2 — Nightscout Hardening: Summary

## Files Changed

| File | Change |
|------|--------|
| `app/services/nightscout_service.py` | Fixed `glucose_unit` → `glucose_units` (silent data bug). Fixed `r[0]` on scalars → `set(scalars().all())` (duplicate-detection-by-first-char bug). |
| `app/api/glucose_ext.py` | `sync_nightscout` route now uses `user.nightscout_url` / `user.nightscout_api_token` instead of non-existent settings-level config. Fixed `datetime.utcnow()` → `datetime.now(timezone.utc)`. |
| `app/services/dexcom_service.py` | Fixed same `glucose_unit` → `glucose_units` bug. |
| `tests/test_nightscout_service.py` | **New file.** 19 tests covering service and API routes. |

## Bugs Found & Fixed

### 1. Silent `glucose_unit` vs `glucose_units`
Both Nightscout and Dexcom services wrote to `glucose_unit` (no "s"), but the ORM model field is `glucose_units`. The value was silently dropped; the column default `"mg/dL"` masked it. Fixed both services.

### 2. Duplicate detection compared first character of stringified timestamps
`set(r[0] for r in scalars())` extracted the first character of each datetime's string representation (e.g. `"2"` from `"2026-05-16..."`), effectively disabling dedup. Fixed to `set(scalars().all())`.

### 3. Nightscout sync endpoint was dead code
`glucose_ext.py:sync_nightscout()` read `settings.NIGHTSCOUT_URL` which doesn't exist in `app/config.py`, always returning 400. Fixed to use `user.nightscout_url` and `user.nightscout_api_token`.

## Test Results: 19/19 passed

```
tests/test_nightscout_service.py::test_connection_success                            PASSED
tests/test_nightscout_service.py::test_connection_http_error                         PASSED
tests/test_nightscout_service.py::test_get_glucose_readings_normalization            PASSED
tests/test_nightscout_service.py::test_get_glucose_readings_empty_response           PASSED
tests/test_nightscout_service.py::test_get_glucose_readings_http_error               PASSED
tests/test_nightscout_service.py::test_get_glucose_readings_auth_error               PASSED
tests/test_nightscout_service.py::test_get_latest_glucose_returns_reading            PASSED
tests/test_nightscout_service.py::test_get_latest_glucose_empty                      PASSED
tests/test_nightscout_service.py::test_auth_headers_with_token                       PASSED
tests/test_nightscout_service.py::test_auth_headers_without_token                    PASSED
tests/test_nightscout_service.py::test_sync_glucose_data_inserts_readings            PASSED
tests/test_nightscout_service.py::test_sync_glucose_data_skips_duplicates            PASSED
tests/test_nightscout_service.py::test_sync_glucose_data_with_real_normalized_readings PASSED
tests/test_nightscout_service.py::test_sync_recent_data                              PASSED
tests/test_nightscout_service.py::test_parse_nightscout_direction                    PASSED
tests/test_nightscout_service.py::test_estimate_trend_rate                           PASSED
tests/test_nightscout_service.py::test_sync_nightscout_route_unconfigured            PASSED
tests/test_nightscout_service.py::test_sync_nightscout_route_success                 PASSED
tests/test_nightscout_service.py::test_sync_nightscout_route_uses_user_config        PASSED
```

## Regression Suite: 120 passed

```text
tests/ai/test_safety.py:             30 passed
tests/test_llm_service.py:           25 passed
tests/test_chat_pipeline.py:          9 passed
tests/test_pattern_service.py:       37 passed
tests/test_nightscout_service.py:    19 passed
                              Total: 120 passed
```

## Test Coverage

| Area | Tests | Type |
|------|-------|------|
| Service connection test | 2 | Unit (mocked HTTP) |
| Glucose reading retrieval | 4 | Unit (mocked HTTP, edge cases) |
| Latest glucose | 2 | Unit |
| Auth headers | 2 | Unit |
| Glucose sync (DB) | 4 | Integration (real DB, mocked API) |
| Helper functions | 2 | Pure unit |
| API routes (TestClient) | 3 | Integration (real DB, mocked service) |

## Open Risks

- Only one Nightscout trend direction per direction value is tested. If Nightscout adds new direction values, the `trend_map` may silently return empty string.
- The `SyncService.sync_glucose_data` uses a `lookback_hours` parameter with no pagination. Very large datasets may hit API limits.
- Route test uses `TestClient` with dependency overrides — covers contract but not real middleware/auth behavior.
