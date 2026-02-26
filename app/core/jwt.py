"""
JWT Token Management - Follows SOLID principles.

Handles creation and validation of JWT access and refresh tokens.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import jwt
from jwt.exceptions import InvalidTokenError

from app.core.logging import get_logger

logger = get_logger(__name__)

# JWT Configuration
# TODO: Move these to environment variables in production
SECRET_KEY = "your-secret-key-change-this-in-production-use-env-variable"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 1  # 1 day as requested
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days
SETUP_TOKEN_EXPIRE_HOURS = 24  # 24 hours


class JWTHandler:
    """
    JWT Token Handler following SOLID principles.

    Single Responsibility: Only handles JWT token operations
    Open/Closed: Can be extended for different token types
    Dependency Inversion: Uses abstractions (doesn't depend on concrete implementations)
    """

    def __init__(
        self,
        secret_key: str = SECRET_KEY,
        algorithm: str = ALGORITHM,
        access_token_expire_days: int = ACCESS_TOKEN_EXPIRE_DAYS,
        refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
        setup_token_expire_hours: int = SETUP_TOKEN_EXPIRE_HOURS
    ):
        """Initialize JWT handler with configuration."""
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_days = access_token_expire_days
        self.refresh_token_expire_days = refresh_token_expire_days
        self.setup_token_expire_hours = setup_token_expire_hours

    def create_access_token(
        self,
        user_id: UUID,
        company_id: UUID,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            user_id: User ID to encode in token
            company_id: Company ID to encode in token (for multi-tenant)
            additional_data: Additional claims to include

        Returns:
            Encoded JWT token string
        """
        expire = datetime.utcnow() + timedelta(days=self.access_token_expire_days)

        to_encode = {
            "sub": str(user_id),  # Subject (user ID)
            "company_id": str(company_id),  # Multi-tenant isolation
            "exp": expire,  # Expiration time
            "iat": datetime.utcnow(),  # Issued at
            "type": "access"  # Token type
        }

        # Add any additional data
        if additional_data:
            to_encode.update(additional_data)

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Created access token for user {user_id}, expires at {expire}")
        return encoded_jwt

    def create_refresh_token(
        self,
        user_id: UUID,
        company_id: UUID
    ) -> str:
        """
        Create JWT refresh token.

        Args:
            user_id: User ID to encode in token
            company_id: Company ID to encode in token

        Returns:
            Encoded JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode = {
            "sub": str(user_id),
            "company_id": str(company_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Created refresh token for user {user_id}, expires at {expire}")
        return encoded_jwt

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string to verify
            token_type: Expected token type ("access" or "refresh")

        Returns:
            Decoded token payload

        Raises:
            InvalidTokenError: If token is invalid, expired, or wrong type
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # Verify token type
            if payload.get("type") != token_type:
                raise InvalidTokenError(f"Invalid token type. Expected '{token_type}'")

            logger.debug(f"Successfully verified {token_type} token for user {payload.get('sub')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise InvalidTokenError(f"Invalid token: {str(e)}")

    def create_setup_token(self, email: str) -> str:
        """
        Create JWT setup token for magic link company setup.

        Args:
            email: Email address to encode in token

        Returns:
            Encoded JWT token string
        """
        expire = datetime.utcnow() + timedelta(hours=self.setup_token_expire_hours)

        to_encode = {
            "sub": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "setup"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Created setup token for email {email}, expires at {expire}")
        return encoded_jwt

    def decode_token_without_verification(self, token: str) -> Dict[str, Any]:
        """
        Decode token without verification (useful for debugging).

        WARNING: Do not use for authentication!

        Args:
            token: JWT token string

        Returns:
            Decoded token payload
        """
        return jwt.decode(token, options={"verify_signature": False})


# Singleton instance
jwt_handler = JWTHandler()


# Convenience functions for backward compatibility
def create_access_token(user_id: UUID, company_id: UUID, **kwargs) -> str:
    """Create access token (convenience function)."""
    return jwt_handler.create_access_token(user_id, company_id, kwargs if kwargs else None)


def create_refresh_token(user_id: UUID, company_id: UUID) -> str:
    """Create refresh token (convenience function)."""
    return jwt_handler.create_refresh_token(user_id, company_id)


def verify_access_token(token: str) -> Dict[str, Any]:
    """Verify access token (convenience function)."""
    return jwt_handler.verify_token(token, token_type="access")


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """Verify refresh token (convenience function)."""
    return jwt_handler.verify_token(token, token_type="refresh")


def create_setup_token(email: str) -> str:
    """Create setup token (convenience function)."""
    return jwt_handler.create_setup_token(email)


def verify_setup_token(token: str) -> Dict[str, Any]:
    """Verify setup token (convenience function)."""
    return jwt_handler.verify_token(token, token_type="setup")
