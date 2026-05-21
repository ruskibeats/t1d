# Clanker Ops #143: [IMPLEMENT] Add hybrid metadata storage to User model

Status: pending
Owner: @clanker
Tags: #implementation #database #migration
Branch: research/synthea-ingestion

## Intended Outcome

The `tbl_users` table is extended with hybrid storage for synthetic patient metadata: 8 core queryable columns for filtering/sorting plus a `synthetic_metadata` JSON blob for the full rich metadata set. An Alembic migration is created and applied. This enables the `SyntheticIngestionMapper` (task #142) to store and query synthetic patient data efficiently.

## Step-by-Step

1. **Read existing model**: Read `app/db/models.py` (User class, lines 35-120) to understand current column definitions and `__table_args__`.

2. **Read existing migration setup**: Read `alembic/versions/` to understand the latest migration and naming convention. Read `alembic/env.py` to understand the migration configuration.

3. **Add columns to User model**: In `app/db/models.py`, add the following columns to the `User` class:
   - `synthetic_id: Mapped[str | None] = Column(String(64), nullable=True, index=True)` — unique synthetic patient identifier
   - `synthetic_diabetes_type: Mapped[str | None] = Column(String(50), nullable=True)` — Type 1 / Type 2 / prediabetes
   - `synthetic_age_range: Mapped[str | None] = Column(String(20), nullable=True)` — child / adolescent / adult / elderly
   - `synthetic_glucose_profile: Mapped[str | None] = Column(String(30), nullable=True)` — well-controlled / high-variability / frequent-hypo
   - `synthetic_data_quality_score: Mapped[float | None] = Column(Float, nullable=True)` — 0-1 completeness metric
   - `synthetic_validation_status: Mapped[str | None] = Column(String(20), nullable=True, index=True)` — passed / failed
   - `synthetic_source: Mapped[str | None] = Column(String(30), nullable=True)` — synthea / simglucose / manual
   - `synthetic_seed_version: Mapped[str | None] = Column(String(30), nullable=True)` — version of rules/config used
   - `synthetic_metadata: Mapped[dict | None] = Column(JSON, nullable=True)` — full rich metadata JSON blob

4. **Add composite index**: Add `Index("ix_users_synthetic_source_status", "synthetic_source", "synthetic_validation_status")` to `__table_args__` for efficient filtering of synthetic patients by source and validation status.

5. **Create Alembic migration**: Run `alembic revision --autogenerate -m "add synthetic patient metadata columns to tbl_users"` in the project root. Verify the generated migration file in `alembic/versions/` contains:
   - `upgrade()`: Adds all 9 columns and the composite index
   - `downgrade()`: Drops all 9 columns and the composite index
   - No unintended changes to other tables

6. **Apply migration**: Run `alembic upgrade head` to apply the migration.

7. **Verify schema**: Run `python -c "from app.db.models import User; print([c.name for c in User.__table__.columns if 'synthetic' in c.name])"` and confirm all 9 columns are listed.

8. **Update Pydantic models**: In `app/models/user.py`, update `UserResponse` to include the new synthetic fields so they are exposed in the API response:
   - `synthetic_id: str | None`
   - `synthetic_diabetes_type: str | None`
   - `synthetic_glucose_profile: str | None`
   - `synthetic_data_quality_score: float | None`
   - `synthetic_validation_status: str | None`
   - `synthetic_source: str | None`

9. **Add model_config update**: Ensure `UserResponse` handles the new nullable fields correctly with `model_config = ConfigDict(from_attributes=True)`.

## Verification

- `alembic upgrade head` completes without errors
- `python -c "from app.db.models import User; print([c.name for c in User.__table__.columns if 'synthetic' in c.name])"` outputs all 9 column names
- `pytest tests/test_api_auth.py` passes (UserResponse serialization still works)
- `grep -c "synthetic_" app/db/models.py` returns at least 9 (one per column)
- Migration file exists in `alembic/versions/` with both `upgrade()` and `downgrade()` functions

## Dependencies

- None (this is the first storage task; #142 depends on it)

## Audit (EOD Report-Back)

Completed by the agent at task completion. Record:
- **Tokens consumed**: approximate total
- **Files changed**: list of modified/created files
- **Stages completed**: which steps were done
- **Stages deferred**: which steps remain (if any)
- **Unexpected issues**: blockers, wrong assumptions, or bugs encountered
- **Artifacts left behind**: temp files, worktrees, debug output
