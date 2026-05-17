"""User API models (Pydantic schemas)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


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
    first_name: str | None = Field(None, description="User first name")
    last_name: str | None = Field(None, description="User last name")

    model_config = ConfigDict(
        from_attributes=True,
    )

    @model_validator(mode='after')
    def split_full_name(self):
        if self.full_name and not self.first_name:
            parts = self.full_name.split(' ', 1)
            self.first_name = parts[0]
            self.last_name = parts[1] if len(parts) > 1 else None
        return self


class UserLogin(BaseModel):
    """User login model."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class Token(BaseModel):
    """Token response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class LoginResponse(BaseModel):
    """Login response model — token + user data."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User profile")
