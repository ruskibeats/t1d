# Clanker Ops #138: [SPRINT 12] Warning cleanup

Status: pending
Owner: @clanker
Tags: #sprint #code-quality
Branch: sprint-12/warning-cleanup

## Intended Outcome

Resolve all Pydantic V2 and SQLAlchemy deprecation warnings in the codebase, ensuring the system runs cleanly without noise during development and testing.

## Step-by-Step

1.  **Identify warnings**: Run `pytest` and `uvicorn` and capture CI/test output to identify active deprecation warnings.
2.  **Pydantic Analysis**:
    - Locate Pydantic models.
    - Update syntax for V2 compliance (`model_validator`, `Field` updates, etc.).
    - Check import paths (e.g., `pydantic.v1` vs `pydantic`).
3.  **SQLAlchemy Analysis**:
    - Identify deprecated usage (e.g., older query methods, attribute access).
    - Refactor to modern ORM patterns.
4.  **Execute Fixes**: Apply changes to the identified files.
5.  **Validate**: Run the full test suite to ensure functionality remains intact.

## Verification

- Run `pytest` without deprecation/warning output (or suppressed expected warnings).
- Ensure no new warnings are generated during API startup or endpoint tests.

## Dependencies

- None.

## Audit (EOD Report-Back)

Completed by the agent at task completion. Record:
- **Tokens consumed**: approximate total
- **Files changed**: list of modified/created files
- **Stages completed**: which steps were done
- **Stages deferred**: which steps remain (if any)
- **Unexpected issues**: blockers, wrong assumptions, or bugs encountered
- **Artifacts left behind**: temp files, worktrees, debug output
