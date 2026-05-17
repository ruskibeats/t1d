"""Authentication API endpoints."""

from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AuthenticationError
from app.core.security import (
    authenticate_user,
    create_user_token,
    require_active_user,
)
from app.db.models import User
from app.models.user import LoginResponse, Token, UserCreate, UserLogin, UserResponse, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user.
    
    Args:
        user_data: User registration data
        session: Database session
        
    Returns:
        UserResponse: Created user
        
    Raises:
        HTTPException: 400 if email already registered, 422 if validation fails
    """
    from sqlalchemy import select

    from app.db.models import User

    # Check if email already exists
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    hashed_password = create_user_token.__globals__['get_password_hash'](user_data.password)

    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        timezone=user_data.timezone,
        diabetes_type=user_data.diabetes_type,
        is_active=True,
        is_verified=False,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Login with email and password.
    
    Args:
        form_data: Login form data
        session: Database session
        
    Returns:
        LoginResponse: Access token + user data
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    user = await authenticate_user(session, form_data.username, form_data.password)

    if not user:
        raise AuthenticationError()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive",
        )

    token = create_user_token(user)
    return LoginResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/login-with-email", response_model=LoginResponse)
async def login_with_email(
    login_data: UserLogin,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Login with email and password (JSON body).
    
    Args:
        login_data: Login data
        session: Database session
        
    Returns:
        LoginResponse: Access token + user data
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    user = await authenticate_user(session, login_data.email, login_data.password)

    if not user:
        raise AuthenticationError()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive",
        )

    token = create_user_token(user)
    return LoginResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(require_active_user),
) -> UserResponse:
    """Get current user information.
    
    Args:
        user: Current authenticated user
        
    Returns:
        UserResponse: Current user information
    """
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    user: User = Depends(require_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update current user information.
    
    Args:
        user_data: Updated user data
        user: Current authenticated user
        session: Database session
        
    Returns:
        UserResponse: Updated user information
    """
    from sqlalchemy import select

    # Check if email is being changed and if it already exists
    if user_data.email is not None and user_data.email != user.email:
        result = await session.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        user.email = user_data.email

    # Update user fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    user.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/dexcom/callback")
# TODO: Add rate limiting (@limiter.limit("5/minute")) when slowapi is installed
async def dexcom_callback(
    code: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    """Handle Dexcom OAuth2 callback.
    
    Args:
        code: Authorization code from Dexcom
        session: Database session
        user: Current authenticated user
        
    Returns:
        Dict: Success response with token info
        
    Raises:
        HTTPException: 400 if callback fails
    """
    from app.services.dexcom_service import DexcomService, DexcomServiceError
    from app.config import get_settings
    
    settings = get_settings()
    
    try:
        dexcom = DexcomService(
            client_id=settings.DEXCOM_CLIENT_ID,
            client_secret=settings.DEXCOM_CLIENT_SECRET,
            redirect_uri=settings.DEXCOM_REDIRECT_URI,
            use_sandbox=settings.DEXCOM_USE_SANDBOX,
        )
        
        tokens = await dexcom.exchange_code_for_tokens(code)
        
        # Update user with Dexcom tokens
        user.dexcom_access_token = tokens.access_token
        user.dexcom_refresh_token = tokens.refresh_token
        user.dexcom_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.expires_in)
        user.updated_at = datetime.now(timezone.utc)
        
        await session.commit()
        await session.refresh(user)
        
        return {
            "message": "Dexcom connected successfully",
            "user_id": user.id,
            "token_type": tokens.token_type,
            "expires_in": tokens.expires_in,
        }
        
    except DexcomServiceError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Dexcom callback failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Dexcom callback error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during Dexcom callback",
        )


@router.post("/dexcom/disconnect")
async def dexcom_disconnect(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    """Disconnect Dexcom account.
    
    Args:
        session: Database session
        user: Current authenticated user
        
    Returns:
        Dict: Success response
    """
    user.dexcom_access_token = None
    user.dexcom_refresh_token = None
    user.dexcom_expires_at = None
    user.updated_at = datetime.now(timezone.utc)
    
    await session.commit()
    
    return {
        "message": "Dexcom disconnected successfully",
    }


@router.post("/verify-email")
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Verify user email with token.
    
    Args:
        token: Verification token
        session: Database session
        
    Returns:
        Dict: Success response
        
    Raises:
        HTTPException: 400 if token is invalid
    """
    # Note: This is a placeholder - actual implementation will generate and verify tokens
    return {
        "message": "Email verification successful",
    }


@router.post("/resend-verification")
async def resend_verification(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    """Resend email verification.
    
    Args:
        session: Database session
        user: Current authenticated user
        
    Returns:
        Dict: Success response
        
    Raises:
        HTTPException: 400 if email is already verified
    """
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified",
        )

    # Note: This is a placeholder - actual implementation will send email
    return {
        "message": "Verification email sent",
    }


@router.post("/forgot-password")
async def forgot_password(
    email: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Request password reset.
    
    Args:
        email: User email
        session: Database session
        
    Returns:
        Dict: Success response (even if email not found for security)
    """
    # Note: This is a placeholder - actual implementation will generate reset token
    return {
        "message": "If an account exists with this email, a reset link has been sent",
    }


@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reset password with token.
    
    Args:
        token: Reset token
        new_password: New password
        session: Database session
        
    Returns:
        Dict: Success response
        
    Raises:
        HTTPException: 400 if token is invalid
    """
    # Note: This is a placeholder - actual implementation will verify token and update password
    return {
        "message": "Password reset successful",
    }
