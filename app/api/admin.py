"""Admin API endpoints for feature flags and meal forecast debugging.

Protected by is_superuser check on the User model.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.services.feature_flags import (
    FeatureFlag,
    FeatureFlagState,
    resolve_flags,
    set_global_flag,
    set_user_override,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ──────────────────────────────────────────────
# Admin auth dependency
# ──────────────────────────────────────────────


async def require_superuser(user: User = Depends(require_active_user)) -> User:
    """Ensure the user is a superuser/admin.

    Args:
        user: Current authenticated user.

    Returns:
        User: The superuser.

    Raises:
        HTTPException: 403 if user is not a superuser.
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────


class FlagSchema(BaseModel):
    """A single feature flag with its current value."""
    flag_name: str
    flag_value: bool
    scope: str = Field(default="global", description="global, user_override, or env_default")


class FlagSetRequest(BaseModel):
    """Request to set a feature flag value."""
    value: bool
    description: str | None = None


class FlagStateResponse(BaseModel):
    """Response with all feature flag states for a user."""
    flags: list[FlagSchema]
    resolved: FeatureFlagState


class FlagSetResponse(BaseModel):
    """Response after setting a feature flag."""
    flag_name: str
    flag_value: bool
    scope: str
    message: str


class DebugForecastResponse(BaseModel):
    """Structured debug information for a meal forecast."""
    forecast_id: str
    resolved_flags: FeatureFlagState
    timestamp: str
    message: str


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────


@router.get("/flags", response_model=FlagStateResponse)
async def list_flags(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superuser),
) -> FlagStateResponse:
    """List all feature flags and their resolved states for the admin user.

    Returns both the raw flag values and the resolved FeatureFlagState.
    """
    resolved = await resolve_flags(db, user.id)
    flags = []
    for flag in FeatureFlag:
        flags.append(FlagSchema(
            flag_name=flag.value,
            flag_value=getattr(resolved, flag.value),
            scope="resolved",
        ))

    logger.info(
        "Admin: listed feature flags",
        extra={"admin_user_id": user.id},
    )

    return FlagStateResponse(flags=flags, resolved=resolved)


@router.post("/flags/{flag_name}", response_model=FlagSetResponse)
async def set_flag(
    flag_name: str,
    data: FlagSetRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superuser),
) -> FlagSetResponse:
    """Set a global feature flag value.

    Args:
        flag_name: The feature flag name (must be a valid FeatureFlag).
        data: The new value and optional description.

    Returns:
        Confirmation with the new flag state.
    """
    # Validate flag name
    try:
        flag = FeatureFlag(flag_name)
    except ValueError:
        valid = [f.value for f in FeatureFlag]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid flag name '{flag_name}'. Valid flags: {valid}",
        )

    await set_global_flag(db, flag, data.value)

    logger.info(
        "Admin: set global feature flag",
        extra={
            "admin_user_id": user.id,
            "flag": flag_name,
            "value": data.value,
        },
    )

    return FlagSetResponse(
        flag_name=flag_name,
        flag_value=data.value,
        scope="global",
        message=f"Global flag '{flag_name}' set to {data.value}",
    )


@router.post("/flags/{flag_name}/user/{target_user_id}", response_model=FlagSetResponse)
async def set_user_flag_override(
    flag_name: str,
    target_user_id: int,
    data: FlagSetRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superuser),
) -> FlagSetResponse:
    """Set a per-user feature flag override.

    Args:
        flag_name: The feature flag name.
        target_user_id: The user to set the override for.
        data: The new value.

    Returns:
        Confirmation with the new flag state.
    """
    try:
        flag = FeatureFlag(flag_name)
    except ValueError:
        valid = [f.value for f in FeatureFlag]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid flag name '{flag_name}'. Valid flags: {valid}",
        )

    # Verify target user exists
    result = await db.execute(select(User).where(User.id == target_user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {target_user_id} not found",
        )

    await set_user_override(db, target_user_id, flag, data.value)

    logger.info(
        "Admin: set user feature flag override",
        extra={
            "admin_user_id": user.id,
            "target_user_id": target_user_id,
            "flag": flag_name,
            "value": data.value,
        },
    )

    return FlagSetResponse(
        flag_name=flag_name,
        flag_value=data.value,
        scope="user_override",
        message=f"User '{target_user_id}' override for '{flag_name}' set to {data.value}",
    )


@router.get("/flags/{flag_name}", response_model=FlagSchema)
async def get_flag(
    flag_name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superuser),
) -> FlagSchema:
    """Get the resolved value of a specific feature flag for the admin user."""
    try:
        flag = FeatureFlag(flag_name)
    except ValueError:
        valid = [f.value for f in FeatureFlag]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid flag name '{flag_name}'. Valid flags: {valid}",
        )

    resolved = await resolve_flags(db, user.id)
    return FlagSchema(
        flag_name=flag.value,
        flag_value=getattr(resolved, flag.value),
        scope="resolved",
    )


@router.get("/meal-forecast/debug", response_model=DebugForecastResponse)
async def debug_forecast_state(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superuser),
) -> DebugForecastResponse:
    """Get debug information for meal forecast feature flag state.

    Returns the current resolved feature flags relevant to meal forecasting
    so an admin can quickly see what's enabled/disabled.
    """
    resolved = await resolve_flags(db, user.id)

    logger.info(
        "Admin: debug meal forecast state",
        extra={
            "admin_user_id": user.id,
            "resolved_flags": {
                "meal_forecast_enabled": resolved.meal_forecast_enabled,
                "meal_forecast_debug_enabled": resolved.meal_forecast_debug_enabled,
                "meal_forecast_simulator_only": resolved.meal_forecast_simulator_only,
                "meal_forecast_internal_beta": resolved.meal_forecast_internal_beta,
            },
        },
    )

    return DebugForecastResponse(
        forecast_id="current-state",
        resolved_flags=resolved,
        timestamp=datetime.now(timezone.utc).isoformat(),
        message="Meal forecast feature flags (no persisted forecast store yet)",
    )