"""Feature flag service for meal forecast rollout controls.

Supports global, cohort, and user-level flags with env-var defaults
and optional DB overrides for runtime toggles.

Flag resolution order:
1. DB user override (user_feature_overrides table) — highest priority
2. DB global flag (feature_flags table) — medium priority
3. Environment variable / Settings default — lowest priority
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class FeatureFlag(str, Enum):
    """Feature flags for meal forecast rollout."""
    MEAL_FORECAST_ENABLED = "meal_forecast_enabled"
    MEAL_FORECAST_DEBUG_ENABLED = "meal_forecast_debug_enabled"
    MEAL_FORECAST_SIMULATOR_ONLY = "meal_forecast_simulator_only"
    MEAL_FORECAST_INTERNAL_BETA = "meal_forecast_internal_beta"


# Default values — all flags default to True in dev, can be overridden via env
_DEFAULTS: dict[FeatureFlag, bool] = {
    FeatureFlag.MEAL_FORECAST_ENABLED: True,
    FeatureFlag.MEAL_FORECAST_DEBUG_ENABLED: True,
    FeatureFlag.MEAL_FORECAST_SIMULATOR_ONLY: False,
    FeatureFlag.MEAL_FORECAST_INTERNAL_BETA: False,
}


@dataclass
class FeatureFlagState:
    """Resolved state for a set of feature flags."""
    meal_forecast_enabled: bool = True
    meal_forecast_debug_enabled: bool = True
    meal_forecast_simulator_only: bool = False
    meal_forecast_internal_beta: bool = False

    def is_forecast_allowed(self, is_simulator_user: bool = False) -> bool:
        """Check if meal forecasting is allowed for this user.

        Args:
            is_simulator_user: Whether the user is a simulator/test user.

        Returns:
            True if forecasting is allowed.
        """
        if not self.meal_forecast_enabled:
            return False
        if self.meal_forecast_simulator_only and not is_simulator_user:
            return False
        return True


async def resolve_flags(
    db: AsyncSession,
    user_id: int,
    env_overrides: Optional[dict[str, bool]] = None,
) -> FeatureFlagState:
    """Resolve feature flag state for a user.

    Resolution order: DB user override > DB global flag > env var > default.

    Args:
        db: Database session.
        user_id: The user to resolve flags for.
        env_overrides: Optional env-var overrides (from Settings).

    Returns:
        Resolved FeatureFlagState.
    """
    env_overrides = env_overrides or {}
    values: dict[str, bool] = {}

    for flag in FeatureFlag:
        # Start with default
        value = _DEFAULTS[flag]

        # Layer 1: env var override
        env_key = flag.value
        if env_key in env_overrides:
            value = env_overrides[env_key]

        # Layer 2: DB global flag (if feature_flags table exists)
        db_global = await _get_db_global_flag(db, flag)
        if db_global is not None:
            value = db_global

        # Layer 3: DB user override (highest priority)
        db_user = await _get_db_user_override(db, user_id, flag)
        if db_user is not None:
            value = db_user

        values[flag.value] = value

    return FeatureFlagState(
        meal_forecast_enabled=values[FeatureFlag.MEAL_FORECAST_ENABLED],
        meal_forecast_debug_enabled=values[FeatureFlag.MEAL_FORECAST_DEBUG_ENABLED],
        meal_forecast_simulator_only=values[FeatureFlag.MEAL_FORECAST_SIMULATOR_ONLY],
        meal_forecast_internal_beta=values[FeatureFlag.MEAL_FORECAST_INTERNAL_BETA],
    )


async def _get_db_global_flag(
    db: AsyncSession, flag: FeatureFlag
) -> Optional[bool]:
    """Read a global feature flag from the DB.

    Returns None if the table doesn't exist or the flag isn't set.
    """
    try:
        result = await db.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.flag_name == flag.value)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return row.flag_value
    except Exception:
        # Table may not exist yet — fall through to defaults
        pass
    return None


async def _get_db_user_override(
    db: AsyncSession, user_id: int, flag: FeatureFlag
) -> Optional[bool]:
    """Read a user-level feature flag override from the DB.

    Returns None if the table doesn't exist or no override is set.
    """
    try:
        result = await db.execute(
            select(UserFeatureOverrideModel).where(
                UserFeatureOverrideModel.user_id == user_id,
                UserFeatureOverrideModel.flag_name == flag.value,
            )
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return row.flag_value
    except Exception:
        # Table may not exist yet — fall through to defaults
        pass
    return None


async def set_global_flag(db: AsyncSession, flag: FeatureFlag, value: bool) -> None:
    """Set a global feature flag value in the DB.

    Args:
        db: Database session.
        flag: The flag to set.
        value: True to enable, False to disable.
    """
    try:
        result = await db.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.flag_name == flag.value)
        )
        row = result.scalar_one_or_none()
        if row:
            row.flag_value = value
        else:
            row = FeatureFlagModel(flag_name=flag.value, flag_value=value)
            db.add(row)
        await db.commit()
        logger.info(
            "Feature flag updated",
            extra={
                "flag": flag.value,
                "value": value,
                "scope": "global",
            },
        )
    except Exception as e:
        logger.warning(f"Could not persist feature flag to DB: {e}")
        # Fall back to in-memory only — the flag still works via env/defaults


async def set_user_override(
    db: AsyncSession, user_id: int, flag: FeatureFlag, value: bool
) -> None:
    """Set a user-level feature flag override in the DB.

    Args:
        db: Database session.
        user_id: The user to set the override for.
        flag: The flag to set.
        value: True to enable, False to disable.
    """
    try:
        result = await db.execute(
            select(UserFeatureOverrideModel).where(
                UserFeatureOverrideModel.user_id == user_id,
                UserFeatureOverrideModel.flag_name == flag.value,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.flag_value = value
        else:
            row = UserFeatureOverrideModel(
                user_id=user_id, flag_name=flag.value, flag_value=value
            )
            db.add(row)
        await db.commit()
        logger.info(
            "Feature flag user override updated",
            extra={
                "flag": flag.value,
                "value": value,
                "scope": "user",
                "user_id": user_id,
            },
        )
    except Exception as e:
        logger.warning(f"Could not persist user feature flag override to DB: {e}")


# ──────────────────────────────────────────────
# Lazy imports for DB models (may not exist yet)
# ──────────────────────────────────────────────

FeatureFlagModel = None
UserFeatureOverrideModel = None


def _register_models():
    """Register feature flag DB models if they exist."""
    global FeatureFlagModel, UserFeatureOverrideModel
    try:
        from app.services.feature_flags_models import (
            FeatureFlagModel as _FFM,
            UserFeatureOverrideModel as _UFOM,
        )
        FeatureFlagModel = _FFM
        UserFeatureOverrideModel = _UFOM
    except ImportError:
        pass


_register_models()
