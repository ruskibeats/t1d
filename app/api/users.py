"""User management API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_user, require_verified_email
from app.db.models import User
from app.models.user import UserResponse

router = APIRouter()


@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_verified_email),
) -> list[UserResponse]:
    """List all users (admin only).
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        session: Database session
        user: Current authenticated user
        
    Returns:
        List[UserResponse]: List of users
    """
    from sqlalchemy import select

    # Note: In production, add admin role check here
    result = await session.execute(
        select(User)
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()

    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> UserResponse:
    """Get user by ID.
    
    Args:
        user_id: User ID
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        UserResponse: User information
        
    Raises:
        HTTPException: 404 if user not found, 403 if not authorized
    """
    from fastapi import HTTPException, status
    from sqlalchemy import select

    # Users can only view their own profile unless admin
    if current_user.id != user_id:
        # Note: In production, add admin role check here
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user",
        )

    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> None:
    """Delete user.
    
    Args:
        user_id: User ID
        session: Database session
        current_user: Current authenticated user
        
    Raises:
        HTTPException: 404 if user not found, 403 if not authorized
    """
    from fastapi import HTTPException, status
    from sqlalchemy import select

    # Users can only delete their own account
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user",
        )

    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await session.delete(user)
    await session.commit()


# -------------------------------------------------------------------
# Nightscout Configuration Endpoints
# -------------------------------------------------------------------

class NightscoutConfig(BaseModel):
    """Nightscout configuration model."""
    url: str
    api_token: str | None = None


class NightscoutStatus(BaseModel):
    """Nightscout status response model."""
    connected: bool
    url: str | None = None
    last_sync: str | None = None


@router.get("/me/nightscout", response_model=NightscoutStatus)
async def get_nightscout_status(
    user: User = Depends(require_active_user),
) -> NightscoutStatus:
    """Get Nightscout connection status.
    
    Args:
        user: Current authenticated user
        
    Returns:
        NightscoutStatus: Connection status
    """
    return NightscoutStatus(
        connected=user.nightscout_connected,
        url=user.nightscout_url,
        last_sync=user.last_nightscout_sync.isoformat() if user.last_nightscout_sync else None,
    )


@router.post("/me/nightscout")
async def configure_nightscout(
    config: NightscoutConfig,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    """Configure Nightscout connection.
    
    Args:
        config: Nightscout configuration
        session: Database session
        user: Current authenticated user
        
    Returns:
        Dict: Success response
        
    Raises:
        HTTPException: 400 if configuration fails
    """
    from app.services.nightscout_service import NightscoutService
    
    nightscout = NightscoutService(
        base_url=config.url,
        api_token=config.api_token,
    )
    
    # Test connection
    try:
        await nightscout._test_connection()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to Nightscout: {str(e)}",
        )
    
    # Save configuration
    user.nightscout_url = config.url
    user.nightscout_api_token = config.api_token
    user.nightscout_connected = True
    user.updated_at = datetime.now(timezone.utc)
    
    await session.commit()
    
    return {
        "message": "Nightscout connected successfully",
        "url": config.url,
    }


@router.delete("/me/nightscout")
async def disconnect_nightscout(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    """Disconnect Nightscout.
    
    Args:
        session: Database session
        user: Current authenticated user
        
    Returns:
        Dict: Success response
    """
    user.nightscout_url = None
    user.nightscout_api_token = None
    user.nightscout_connected = False
    user.updated_at = datetime.now(timezone.utc)
    
    await session.commit()
    
    return {
        "message": "Nightscout disconnected successfully",
    }


@router.post("/me/nightscout/sync")
async def sync_nightscout(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    """Sync glucose data from Nightscout.
    
    Args:
        session: Database session
        user: Current authenticated user
        
    Returns:
        Dict: Sync results
        
    Raises:
        HTTPException: 400 if not configured or sync fails
    """
    from app.services.nightscout_service import NightscoutService
    
    if not user.nightscout_url:
        raise HTTPException(
            status_code=400,
            detail="Nightscout not configured",
        )
    
    nightscout = NightscoutService(
        base_url=user.nightscout_url,
        api_token=user.nightscout_api_token,
    )
    
    try:
        count = await nightscout.sync_glucose_data(session, user)
        user.last_nightscout_sync = datetime.now(timezone.utc)
        await session.commit()
        
        return {
            "message": "Sync successful",
            "readings_imported": count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Sync failed: {str(e)}",
        )
