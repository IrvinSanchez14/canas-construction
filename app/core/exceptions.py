"""Custom exceptions for the application."""

from typing import Any, Optional


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, status_code: int = 500, details: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class NotFoundException(AppException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str, identifier: Any):
        message = f"{resource} with id {identifier} not found"
        super().__init__(message, status_code=404)


class AlreadyExistsException(AppException):
    """Raised when trying to create a resource that already exists."""

    def __init__(self, resource: str, field: str, value: Any):
        message = f"{resource} with {field}='{value}' already exists"
        super().__init__(message, status_code=400)


class ValidationException(AppException):
    """Raised when business validation fails."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, status_code=400, details=details)


class AuthenticationException(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=401)


class AuthorizationException(AppException):
    """Raised when user doesn't have permission."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class DatabaseException(AppException):
    """Raised when database operation fails."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, status_code=500, details=details)
