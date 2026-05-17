"""Security and authentication utilities."""

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.db.models import User

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token data payload."""
    sub: str | None = None
    exp: int | None = None


class UserCreate(BaseModel):
    """User creation model."""
    email: EmailStr
    password: str
    full_name: str | None = None
    diabetes_type: str | None = None
    timezone: str = "UTC"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model (excludes sensitive data)."""
    id: int
    email: str
    full_name: str | None
    timezone: str
    diabetes_type: str | None
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """User update model."""
    full_name: str | None = None
    timezone: str | None = None
    diabetes_type: str | None = None
    target_range_low: float | None = None
    target_range_high: float | None = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        str: JWT token
    """
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData: Decoded token data
        
    Raises:
        JWTError: If token is invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        sub: str | None = payload.get("sub")
        exp: int | None = payload.get("exp")

        if sub is None:
            raise JWTError("Token missing 'sub' claim")

        return TokenData(sub=sub, exp=exp)

    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")


async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> User | None:
    """Get user by email address.
    
    Args:
        session: Database session
        email: User email
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    result = await session.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> User | None:
    """Get user by ID.
    
    Args:
        session: Database session
        user_id: User ID
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user with email and password.
    
    Args:
        session: Database session
        email: User email
        password: Plain text password
        
    Returns:
        Optional[User]: Authenticated user if credentials are valid
    """
    user = await get_user_by_email(session, email)

    if not user or not verify_password(password, user.hashed_password):
        return None

    return user


async def get_current_user(
    session: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Get current authenticated user from token.
    
    Args:
        session: Database session dependency
        token: JWT token (from Authorization header)
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    try:
        token_data = decode_token(token)
        user_id_str = token_data.sub

        if user_id_str is None:
            raise credentials_exception

        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await get_user_by_id(session, user_id)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


async def require_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Ensure user is active.
    
    Args:
        user: Current user (from get_current_user)
        
    Returns:
        User: Active user
        
    Raises:
        HTTPException: 400 if user is not active
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


async def require_verified_email(
    user: User = Depends(require_active_user),
) -> User:
    """Ensure user has verified email.
    
    Args:
        user: Current user (from require_active_user)
        
    Returns:
        User: User with verified email
        
    Raises:
        HTTPException: 403 if email not verified
    """
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )

    return user


def create_user_token(user: User) -> Token:
    """Create access token for a user.
    
    Args:
        user: User object
        
    Returns:
        Token: Token response
    """
    settings = get_settings()

    token_data = {
        "sub": str(user.id),
        "email": user.email,
    }

    expires_delta = timedelta(
        minutes=settings.access_token_expire_minutes
    )

    access_token = create_access_token(token_data, expires_delta)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )
