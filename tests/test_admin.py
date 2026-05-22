"""Tests for admin API endpoints (feature flags + debug).

Exercises:
1. Superuser access control (regular user gets 403)
2. List feature flags
3. Set/get global feature flags
4. Set/get user-level overrides
5. Debug endpoint access
"""

import pytest
import pytest_asyncio
from unittest.mock import patch

from sqlalchemy import select

from app.db.models import User
from app.services.feature_flags import (
    FeatureFlag,
    FeatureFlagState,
    resolve_flags,
    set_global_flag,
    set_user_override,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest_asyncio.fixture
async def superuser(db_session):
    """Create a superuser for admin endpoint tests."""
    user = User(
        email="admin@example.com",
        hashed_password="admin-hash",
        is_active=True,
        is_verified=True,
        is_superuser=True,
        full_name="Admin User",
        timezone="UTC",
        diabetes_type="Type 1",
    )
    db_session.add(user)
    await db_session.commit()
    return user


# ──────────────────────────────────────────────
# Feature Flag Service Tests
# ──────────────────────────────────────────────


class TestFeatureFlagService:
    """Tests for the feature flag service layer."""

    @pytest.mark.asyncio
    async def test_resolve_flags_defaults(self, db_session, test_user):
        """Resolving flags with no overrides returns default values."""
        state = await resolve_flags(db_session, test_user.id)
        assert isinstance(state, FeatureFlagState)
        assert state.meal_forecast_enabled is True
        assert state.meal_forecast_debug_enabled is True
        assert state.meal_forecast_simulator_only is False
        assert state.meal_forecast_internal_beta is False

    @pytest.mark.asyncio
    async def test_resolve_flags_env_override(self, db_session, test_user):
        """Env overrides are applied on top of defaults."""
        overrides = {"meal_forecast_enabled": False}
        state = await resolve_flags(db_session, test_user.id, env_overrides=overrides)
        assert state.meal_forecast_enabled is False

    @pytest.mark.asyncio
    async def test_set_global_flag_persists(self, db_session, test_user):
        """Setting a global flag persists to DB and is reflected in resolve."""
        await set_global_flag(db_session, FeatureFlag.MEAL_FORECAST_ENABLED, False)

        state = await resolve_flags(db_session, test_user.id)
        assert state.meal_forecast_enabled is False

    @pytest.mark.asyncio
    async def test_set_global_flag_toggle(self, db_session, test_user):
        """Global flag can be toggled on and off."""
        await set_global_flag(db_session, FeatureFlag.MEAL_FORECAST_ENABLED, False)
        state = await resolve_flags(db_session, test_user.id)
        assert state.meal_forecast_enabled is False

        await set_global_flag(db_session, FeatureFlag.MEAL_FORECAST_ENABLED, True)
        state = await resolve_flags(db_session, test_user.id)
        assert state.meal_forecast_enabled is True

    @pytest.mark.asyncio
    async def test_user_override_takes_priority(self, db_session, test_user):
        """User-level override takes priority over global flag."""
        await set_global_flag(db_session, FeatureFlag.MEAL_FORECAST_ENABLED, False)
        await set_user_override(db_session, test_user.id, FeatureFlag.MEAL_FORECAST_ENABLED, True)

        state = await resolve_flags(db_session, test_user.id)
        assert state.meal_forecast_enabled is True

    @pytest.mark.asyncio
    async def test_user_override_other_user_unaffected(self, db_session, test_user, test_user_2):
        """User override for one user doesn't affect another user."""
        await set_user_override(db_session, test_user.id, FeatureFlag.MEAL_FORECAST_ENABLED, False)

        state_1 = await resolve_flags(db_session, test_user.id)
        state_2 = await resolve_flags(db_session, test_user_2.id)
        assert state_1.meal_forecast_enabled is False
        assert state_2.meal_forecast_enabled is True

    @pytest.mark.asyncio
    async def test_is_forecast_allowed_checks(self, db_session, test_user):
        """is_forecast_allowed respects all flag combinations."""
        state = await resolve_flags(db_session, test_user.id)
        assert state.is_forecast_allowed() is True

        # Disable globally
        await set_global_flag(db_session, FeatureFlag.MEAL_FORECAST_ENABLED, False)
        state = await resolve_flags(db_session, test_user.id)
        assert state.is_forecast_allowed() is False

        # Enable globally but set simulator-only
        await set_global_flag(db_session, FeatureFlag.MEAL_FORECAST_ENABLED, True)
        await set_global_flag(db_session, FeatureFlag.MEAL_FORECAST_SIMULATOR_ONLY, True)
        state = await resolve_flags(db_session, test_user.id)
        assert state.is_forecast_allowed() is False  # not a simulator user
        assert state.is_forecast_allowed(is_simulator_user=True) is True

    @pytest.mark.asyncio
    async def test_flags_independent_of_each_other(self, db_session, test_user):
        """Each flag can be independently set without affecting others."""
        await set_global_flag(db_session, FeatureFlag.MEAL_FORECAST_SIMULATOR_ONLY, True)

        state = await resolve_flags(db_session, test_user.id)
        assert state.meal_forecast_enabled is True  # unchanged
        assert state.meal_forecast_simulator_only is True
        assert state.meal_forecast_debug_enabled is True  # unchanged
        assert state.meal_forecast_internal_beta is False  # unchanged


# ──────────────────────────────────────────────
# Admin API Endpoint Tests
# ──────────────────────────────────────────────


class TestAdminEndpoints:
    """Tests for the admin API endpoints."""

    # Regular user access control is tested in TestRequireSuperuser below.
    # Calling endpoint functions directly bypasses FastAPI dependency injection,
    # so we test the require_superuser dependency directly.

    @pytest.mark.asyncio
    async def test_superuser_can_list_flags(self, db_session, superuser):
        """Superuser can retrieve all feature flags."""
        from app.api.admin import list_flags

        # Ensure at least one flag is set
        await set_global_flag(db_session, FeatureFlag.MEAL_FORECAST_ENABLED, True)

        result = await list_flags(db_session, superuser)
        assert result is not None
        assert len(result.flags) == 4  # All 4 FeatureFlag values
        assert result.resolved.meal_forecast_enabled is True

    @pytest.mark.asyncio
    async def test_set_global_flag_endpoint(self, db_session, superuser):
        """Superuser can set a global feature flag."""
        from app.api.admin import set_flag
        from app.api.admin import FlagSetRequest

        result = await set_flag(
            flag_name="meal_forecast_enabled",
            data=FlagSetRequest(value=False),
            db=db_session,
            user=superuser,
        )
        assert result.flag_name == "meal_forecast_enabled"
        assert result.flag_value is False
        assert result.scope == "global"

        # Verify it took effect
        state = await resolve_flags(db_session, superuser.id)
        assert state.meal_forecast_enabled is False

    @pytest.mark.asyncio
    async def test_set_global_flag_invalid_name(self, db_session, superuser):
        """Invalid flag name returns 400."""
        from app.api.admin import set_flag
        from app.api.admin import FlagSetRequest
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await set_flag(
                flag_name="nonexistent_flag",
                data=FlagSetRequest(value=True),
                db=db_session,
                user=superuser,
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_set_user_override_endpoint(self, db_session, superuser, test_user):
        """Superuser can set a user-level override."""
        from app.api.admin import set_user_flag_override
        from app.api.admin import FlagSetRequest

        result = await set_user_flag_override(
            flag_name="meal_forecast_enabled",
            target_user_id=test_user.id,
            data=FlagSetRequest(value=False),
            db=db_session,
            user=superuser,
        )
        assert result.flag_value is False
        assert result.scope == "user_override"

        # Verify it took effect for target user
        state = await resolve_flags(db_session, test_user.id)
        assert state.meal_forecast_enabled is False

    @pytest.mark.asyncio
    async def test_set_user_override_nonexistent_user(self, db_session, superuser):
        """Setting override for nonexistent user returns 404."""
        from app.api.admin import set_user_flag_override
        from app.api.admin import FlagSetRequest
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await set_user_flag_override(
                flag_name="meal_forecast_enabled",
                target_user_id=99999,
                data=FlagSetRequest(value=False),
                db=db_session,
                user=superuser,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_flag_endpoint(self, db_session, superuser):
        """Superuser can get a specific flag's resolved value."""
        from app.api.admin import get_flag

        result = await get_flag(
            flag_name="meal_forecast_enabled",
            db=db_session,
            user=superuser,
        )
        assert result.flag_name == "meal_forecast_enabled"
        assert result.flag_value is True  # default

    @pytest.mark.asyncio
    async def test_debug_forecast_state_endpoint(self, db_session, superuser):
        """Superuser can access the debug endpoint."""
        from app.api.admin import debug_forecast_state

        result = await debug_forecast_state(db_session, superuser)
        assert result.forecast_id == "current-state"
        assert result.resolved_flags is not None
        assert isinstance(result.resolved_flags, FeatureFlagState)


class TestRequireSuperuser:
    """Tests for the require_superuser dependency."""

    @pytest.mark.asyncio
    async def test_regular_user_blocked(self, test_user):
        """Regular user is blocked by require_superuser."""
        from app.api.admin import require_superuser
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await require_superuser(test_user)
        assert exc.value.status_code == 403
        assert "Admin access required" in exc.value.detail

    @pytest.mark.asyncio
    async def test_superuser_allowed(self, superuser):
        """Superuser passes require_superuser check."""
        from app.api.admin import require_superuser

        result = await require_superuser(superuser)
        assert result == superuser

    @pytest.mark.asyncio
    async def test_inactive_superuser_blocked(self, db_session):
        """Inactive user is blocked even if is_superuser is True."""
        from app.api.admin import require_superuser
        from app.core.security import require_active_user
        from fastapi import HTTPException

        user = User(
            email="inactive_admin@example.com",
            hashed_password="hash",
            is_active=False,
            is_verified=True,
            is_superuser=True,
        )
        db_session.add(user)
        await db_session.commit()

        # require_active_user should block them first
        with pytest.raises(HTTPException) as exc:
            await require_active_user(user)
        assert exc.value.status_code == 400
        assert "Inactive user" in exc.value.detail