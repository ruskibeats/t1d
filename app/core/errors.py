"""Custom exceptions and error handling for the T1D Companion."""


from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict


class T1DException(Exception):
    """Base exception for T1D Companion application."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(T1DException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(T1DException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class NotFoundError(T1DException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str, identifier: str):
        message = f"{resource} not found: {identifier}"
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ValidationError(T1DException):
    """Raised when data validation fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class DataIntegrityError(T1DException):
    """Raised when data integrity is violated."""

    def __init__(self, message: str = "Data integrity error"):
        super().__init__(message, status.HTTP_409_CONFLICT)


class ExternalAPIError(T1DException):
    """Raised when an external API call fails."""

    def __init__(self, service: str, message: str):
        full_message = f"External API error ({service}): {message}"
        super().__init__(full_message, status.HTTP_502_BAD_GATEWAY)


class SafetyViolationError(T1DException):
    """Raised when a safety rule is violated."""

    def __init__(self, message: str = "Safety check failed"):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    message: str
    detail: dict | None = None
    timestamp: str | None = None

    model_config = ConfigDict(from_attributes=True)


def create_http_exception(status_code: int, detail: str, headers: dict | None = None) -> HTTPException:
    """Create a FastAPI HTTP exception.
    
    Args:
        status_code: HTTP status code
        detail: Error detail message
        headers: Optional headers
        
    Returns:
        HTTPException: FastAPI exception
    """
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers=headers,
    )


# Common error messages
ERROR_MESSAGES = {
    "invalid_credentials": "Invalid email or password",
    "user_not_found": "User not found",
    "user_inactive": "User account is inactive",
    "email_not_verified": "Email not verified",
    "token_expired": "Token has expired",
    "invalid_token": "Invalid or malformed token",
    "missing_token": "Authorization token is missing",
    "insufficient_permissions": "Insufficient permissions",
    "resource_not_found": "Resource not found",
    "duplicate_email": "Email already registered",
    "weak_password": "Password does not meet requirements",
    "invalid_glucose_value": "Invalid glucose value",
    "invalid_timestamp": "Invalid timestamp",
    "data_out_of_range": "Data value out of acceptable range",
    "external_service_unavailable": "External service temporarily unavailable",
    "rate_limit_exceeded": "Rate limit exceeded, please try again later",
    "maintenance_mode": "Service is currently under maintenance",
}
