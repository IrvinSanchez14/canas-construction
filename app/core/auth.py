"""
Authentication dependencies for FastAPI endpoints.

Provides dependency injection for authentication and authorization.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID
from jwt.exceptions import InvalidTokenError

from app.core.database import get_db
from app.core.jwt import verify_access_token
from app.repositories import UserRepository
from app.models import User
from app.core.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    This is the main authentication dependency that should be used
    to protect endpoints.

    Args:
        credentials: HTTP Authorization header with Bearer token
        db: Database session

    Returns:
        Current authenticated user

    Raises:
        HTTPException 401: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract token from credentials
        token = credentials.credentials

        # Verify and decode token
        payload = verify_access_token(token)

        # Extract user ID from token
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception

        user_id = UUID(user_id_str)

    except InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise credentials_exception
    except ValueError as e:
        logger.warning(f"Invalid user ID format: {str(e)}")
        raise credentials_exception

    # Get user from database
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if user is None:
        logger.warning(f"User not found: {user_id}")
        raise credentials_exception

    logger.debug(f"Authenticated user: {user.email} (ID: {user.id})")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current active user.

    Ensures the user is not only authenticated but also active.

    Args:
        current_user: Current authenticated user

    Returns:
        Current active user

    Raises:
        HTTPException 403: If user is inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency to get current superuser.

    Ensures the user is an active superuser.

    Args:
        current_user: Current active user

    Returns:
        Current superuser

    Raises:
        HTTPException 403: If user is not a superuser
    """
    if not current_user.is_superuser:
        logger.warning(f"Non-superuser attempted superuser access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Superuser access required."
        )

    return current_user


def get_company_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    Dependency to extract company ID from JWT token.

    Useful for multi-tenant operations where you need the company ID
    without loading the full user object.

    Args:
        credentials: HTTP Authorization header with Bearer token

    Returns:
        Company ID from token

    Raises:
        HTTPException 401: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = verify_access_token(token)

        company_id_str: str = payload.get("company_id")
        if company_id_str is None:
            raise credentials_exception

        return UUID(company_id_str)

    except (InvalidTokenError, ValueError):
        raise credentials_exception
