"""Authentication schemas for login and token management."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID


class LoginRequest(BaseModel):
    """Schema for user login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class TokenResponse(BaseModel):
    """
    Schema for token response.

    Returns both access and refresh tokens after successful login.
    """
    access_token: str = Field(..., description="JWT access token (expires in 1 day)")
    refresh_token: str = Field(..., description="JWT refresh token (expires in 30 days)")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(default=86400, description="Access token expiration in seconds (1 day = 86400)")


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")


class TokenPayload(BaseModel):
    """Schema for decoded JWT token payload."""
    sub: UUID = Field(..., description="User ID (subject)")
    company_id: UUID = Field(..., description="Company ID for multi-tenant isolation")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    type: str = Field(..., description="Token type (access or refresh)")


class SetupLinkRequest(BaseModel):
    """Schema for requesting a setup magic link."""
    email: EmailStr = Field(..., description="Email address to send setup link to")


class SetupLinkResponse(BaseModel):
    """Schema for setup link response (generic to prevent email enumeration)."""
    message: str = Field(default="If this email is authorized, a setup link has been sent.")


class SetupTokenVerifyResponse(BaseModel):
    """Schema for setup token verification response."""
    valid: bool
    email: Optional[str] = None


class CompanySetupRequest(BaseModel):
    """
    Schema for initial company setup.

    This is used to create the first company and admin user.
    Requires a valid setup token from the magic link flow.
    """
    # Setup token
    setup_token: str = Field(..., description="Setup token from magic link")

    # Company info
    company_name: str = Field(..., min_length=1, max_length=255)
    company_email: EmailStr
    company_phone: Optional[str] = None
    company_address: Optional[str] = None

    # Admin user info
    admin_email: EmailStr
    admin_username: str = Field(..., min_length=3, max_length=100)
    admin_password: str = Field(..., min_length=8, description="Minimum 8 characters")
    admin_first_name: str = Field(..., min_length=1, max_length=100)
    admin_last_name: str = Field(..., min_length=1, max_length=100)
    admin_phone: Optional[str] = None


class CompanySetupResponse(BaseModel):
    """Schema for company setup response."""
    company_id: UUID
    company_name: str
    admin_user_id: UUID
    admin_email: str
    message: str = "Company and admin user created successfully"
