"""User management API endpoints."""


from fastapi import APIRouter, Depends
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
