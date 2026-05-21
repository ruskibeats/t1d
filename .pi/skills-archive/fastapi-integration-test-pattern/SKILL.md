---
name: "fastapi-integration-test-pattern"
description: "Procedure for writing integration tests for FastAPI endpoints, covering dependency overriding and mock coordinator setup."
version: 1
created: "2026-05-20"
updated: "2026-05-20"
---
## When to Use
Use when creating new integration tests for FastAPI endpoints within the T1D Companion codebase to ensure consistency and proper setup of the authentication and service-coordinator stack.

## Procedure
1.  **Mount Target Router**: Ensure the target router is mounted on a fresh `FastAPI()` instance.
2.  **Dependency Overrides**: Use `app.dependency_overrides` to inject patched versions of `get_db`, `require_active_user`, and `get_current_user`.
3.  **Mock Coordinator**: Attach a mock coordinator instance to `app.state.coordinator` to bypass production service chains.
4.  **Test Client**: Use `Starlette.testclient.TestClient` for synchronous HTTP calls.
5.  **Async/Sync Verification**: Mark test functions with `@pytest.mark.asyncio` for any async database or service logic assertions.
6.  **Teardown**: Always include a fixture or finalizer to clear `app.dependency_overrides` after each test to prevent state pollution.

## Pitfalls
*   **Pollution**: Not resetting `app.dependency_overrides` makes tests flaky and dependent on execution order.
*   **Initialization**: Omitting the mock coordinator in `app.state` almost always causes runtime errors in the Service layer.

## Verification
Refer to `tests/test_chat_integration.py` and `tests/test_api_auth.py` for canonical implementations.