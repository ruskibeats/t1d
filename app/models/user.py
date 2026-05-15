"""User API models (Pydantic schemas)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user model."""

    email: EmailStr = Field(..., description="User email address")
    full_name: str | None = Field(None, description="User full name", max_length=255)
    timezone: str = Field("UTC", description="User timezone")
    diabetes_type: str | None = Field(None, description="Type of diabetes")


class UserCreate(UserBase):
    """User creation model."""

    password: str = Field(..., min_length=8, description="User password (min 8 chars)")
    confirm_password: str = Field(..., description="Confirm password")


class UserUpdate(BaseModel):
    """User update model."""

    full_name: str | None = Field(None, description="User full name", max_length=255)
    timezone: str | None = Field(None, description="User timezone")
    diabetes_type: str | None = Field(None, description="Type of diabetes")
    target_range_low: float | None = Field(None, description="Target glucose range low")
    target_range_high: float | None = Field(None, description="Target glucose range high")


class UserResponse(UserBase):
    """User response model."""

    id: int = Field(..., description="User ID")
    is_active: bool = Field(..., description="Is user active")
    is_verified: bool = Field(..., description="Is email verified")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_glucose_sync: datetime | None = Field(None, description="Last glucose sync timestamp")
    dexcom_connected: bool = Field(False, description="Whether Dexcom is connected")

    model_config = ConfigDict(
        from_attributes=True,
    )


class UserLogin(BaseModel):
    """User login model."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class Token(BaseModel):
    """Token response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
