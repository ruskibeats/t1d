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
    nightscout_connected: bool = Field(False, description="Whether Nightscout is connected")
    nightscout_url: str | None = Field(None, description="Nightscout URL")
    last_nightscout_sync: datetime | None = Field(None, description="Last Nightscout sync timestamp")
    librelinkup_connected: bool = Field(False, description="Whether LibreLinkUp is connected")
    last_librelinkup_sync: datetime | None = Field(None, description="Last LibreLinkUp sync timestamp")
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


class DexcomConnectionDetail(BaseModel):
    """Dexcom connection status detail."""
    connected: bool = Field(False, description="Whether Dexcom is connected")
    has_valid_token: bool = Field(False, description="Whether the OAuth token is valid and unexpired")
    expires_at: datetime | None = Field(None, description="Token expiration time")
    last_sync: datetime | None = Field(None, description="Last successful sync")


class NightscoutConnectionDetail(BaseModel):
    """Nightscout connection status detail."""
    connected: bool = Field(False, description="Whether Nightscout is connected")
    url: str | None = Field(None, description="Nightscout URL")
    has_token: bool = Field(False, description="Whether API token is configured")
    last_sync: datetime | None = Field(None, description="Last successful sync")


class LibreLinkUpConnectionDetail(BaseModel):
    """LibreLinkUp connection status detail."""
    connected: bool = Field(False, description="Whether LibreLinkUp is connected")
    email: str | None = Field(None, description="LibreLinkUp account email")
    region: str | None = Field(None, description="API region")
    last_sync: datetime | None = Field(None, description="Last successful sync")


class CGMConnectionStatus(BaseModel):
    """Consolidated CGM connection status."""

    dexcom: DexcomConnectionDetail = Field(..., description="Dexcom connection details")
    nightscout: NightscoutConnectionDetail = Field(..., description="Nightscout connection details")
    librelinkup: LibreLinkUpConnectionDetail = Field(..., description="LibreLinkUp connection details")
    any_connected: bool = Field(..., description="Whether any CGM source is connected")
    last_sync: datetime | None = Field(None, description="Most recent sync across all sources")


class NightscoutTestResult(BaseModel):
    """Nightscout connection test result."""
    success: bool = Field(..., description="Whether the connection test succeeded")
    message: str = Field(..., description="Human-readable result")
    latest_reading: dict | None = Field(None, description="Latest glucose reading, if available")
    readings_24h: int | None = Field(None, description="Number of readings in last 24 hours")


class LibreLinkUpTestResult(BaseModel):
    """LibreLinkUp connection test result."""
    success: bool = Field(..., description="Whether the connection test succeeded")
    message: str = Field(..., description="Human-readable result")
    patient_name: str | None = Field(None, description="Connected patient name")
    latest_value: float | None = Field(None, description="Latest glucose value in mg/dL")
    latest_trend: str | None = Field(None, description="Latest trend direction")
    readings_count: int | None = Field(None, description="Number of readings fetched")


class CGMConnectResponse(BaseModel):
    """Response after connecting a CGM source."""
    success: bool = Field(..., description="Whether the connection was successful")
    message: str = Field(..., description="Human-readable message")
    source: str = Field(..., description="Connected CGM source (dexcom or nightscout)")


class DexcomAuthUrlResponse(BaseModel):
    """Dexcom OAuth authorization URL response."""
    auth_url: str = Field(..., description="Dexcom OAuth authorization URL")
    state: str = Field(..., description="CSRF state token")
