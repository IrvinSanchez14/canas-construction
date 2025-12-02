"""
Global exception handlers for FastAPI.

Converts custom exceptions to proper HTTP responses automatically.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.exceptions import (
    AppException,
    NotFoundException,
    AlreadyExistsException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    DatabaseException
)
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle all custom application exceptions.

    Converts AppException and its subclasses to JSON responses.
    """
    logger.error(
        f"AppException: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path
        }
    )


async def not_found_exception_handler(request: Request, exc: NotFoundException) -> JSONResponse:
    """Handle NotFoundException (404)."""
    logger.warning(f"Not found: {exc.message} - Path: {request.url.path}")

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "NotFound",
            "message": exc.message,
            "path": request.url.path
        }
    )


async def already_exists_exception_handler(request: Request, exc: AlreadyExistsException) -> JSONResponse:
    """Handle AlreadyExistsException (400)."""
    logger.warning(f"Resource already exists: {exc.message}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "AlreadyExists",
            "message": exc.message,
            "path": request.url.path
        }
    )


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    """Handle ValidationException (400)."""
    logger.warning(f"Validation error: {exc.message}", extra={"details": exc.details})

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "ValidationError",
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path
        }
    )


async def authentication_exception_handler(request: Request, exc: AuthenticationException) -> JSONResponse:
    """Handle AuthenticationException (401)."""
    logger.warning(f"Authentication failed: {exc.message} - Path: {request.url.path}")

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Unauthorized",
            "message": exc.message,
            "path": request.url.path
        },
        headers={"WWW-Authenticate": "Bearer"}
    )


async def authorization_exception_handler(request: Request, exc: AuthorizationException) -> JSONResponse:
    """Handle AuthorizationException (403)."""
    logger.warning(f"Authorization failed: {exc.message} - Path: {request.url.path}")

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "Forbidden",
            "message": exc.message,
            "path": request.url.path
        }
    )


async def database_exception_handler(request: Request, exc: DatabaseException) -> JSONResponse:
    """Handle DatabaseException (500)."""
    logger.error(
        f"Database error: {exc.message}",
        extra={"details": exc.details, "path": request.url.path}
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "DatabaseError",
            "message": "An error occurred while accessing the database",
            "path": request.url.path
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors (422).

    These occur when request data doesn't match schema.
    """
    # Handle OPTIONS requests with CORS headers manually
    # Error handlers run after middleware, so we need to add CORS headers ourselves
    if request.method == "OPTIONS":
        origin = request.headers.get("origin")
        if origin and origin in settings.CORS_ORIGINS:
            response = Response(status_code=200)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            return response
        return Response(status_code=200)

    logger.warning(f"Request validation error: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Invalid request data",
            "details": exc.errors(),
            "path": request.url.path
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """
    Handle SQLAlchemy integrity errors (unique constraint, foreign key, etc).

    This is a fallback for database errors that slip through business logic.
    """
    logger.error(f"Database integrity error: {str(exc.orig)}")

    # Try to extract meaningful message
    error_msg = str(exc.orig)
    if "unique constraint" in error_msg.lower():
        message = "A record with this value already exists"
    elif "foreign key constraint" in error_msg.lower():
        message = "Referenced record does not exist"
    elif "not null constraint" in error_msg.lower():
        message = "Required field is missing"
    else:
        message = "Database constraint violation"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "IntegrityError",
            "message": message,
            "path": request.url.path
        }
    )


async def operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """
    Handle SQLAlchemy operational errors (connection issues, etc).
    """
    logger.critical(f"Database operational error: {str(exc.orig)}")

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "ServiceUnavailable",
            "message": "Database temporarily unavailable. Please try again later.",
            "path": request.url.path
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    This prevents exposing internal errors to users.
    """
    # Handle OPTIONS requests with CORS headers manually
    # Error handlers run after middleware, so we need to add CORS headers ourselves
    if request.method == "OPTIONS":
        origin = request.headers.get("origin")
        if origin and origin in settings.CORS_ORIGINS:
            response = Response(status_code=200)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            return response
        return Response(status_code=200)

    logger.exception(
        f"Unhandled exception: {str(exc)}",
        extra={"path": request.url.path, "method": request.method}
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please contact support if this persists.",
            "path": request.url.path
        }
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.

    Call this in main.py after creating the app.
    """
    # Custom exceptions
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(NotFoundException, not_found_exception_handler)
    app.add_exception_handler(AlreadyExistsException, already_exists_exception_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(AuthenticationException, authentication_exception_handler)
    app.add_exception_handler(AuthorizationException, authorization_exception_handler)
    app.add_exception_handler(DatabaseException, database_exception_handler)

    # FastAPI/Pydantic exceptions
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # SQLAlchemy exceptions
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(OperationalError, operational_error_handler)

    # Catch-all for unexpected errors
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered")
