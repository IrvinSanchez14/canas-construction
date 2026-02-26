"""
Authentication endpoints - Login, Token Refresh, and Company Setup.

These endpoints do NOT require authentication (they generate authentication).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.jwt import create_access_token, create_refresh_token, verify_refresh_token, create_setup_token, verify_setup_token
from app.core.password import password_hasher
from app.repositories import UserRepository, CompanyRepository, RoleRepository
from app.services import UserService, CompanyService, RoleService
from app.services.email_service import EmailService
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    SetupLinkRequest,
    SetupLinkResponse,
    SetupTokenVerifyResponse,
    CompanySetupRequest,
    CompanySetupResponse
)
from app.core.logging import get_logger
from jwt.exceptions import InvalidTokenError

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    User login endpoint.

    Authenticates user and returns access and refresh tokens.

    **No authentication required** - this generates the tokens.

    **Token Expiration:**
    - Access Token: 1 day (86400 seconds)
    - Refresh Token: 30 days

    **Usage:**
    1. Call this endpoint with email and password
    2. Receive access_token and refresh_token
    3. Use access_token in Authorization header for all subsequent requests
    4. When access_token expires, use refresh_token to get new tokens

    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/auth/login" \\
      -H "Content-Type: application/json" \\
      -d '{"email": "user@example.com", "password": "password123"}'
    ```
    """
    logger.info(f"Login attempt for email: {login_data.email}")

    # Initialize repositories
    user_repo = UserRepository(db)
    company_repo = CompanyRepository(db)
    role_repo = RoleRepository(db)

    # Initialize user service
    user_service = UserService(
        user_repository=user_repo,
        company_repository=company_repo,
        role_repository=role_repo,
        password_hasher=password_hasher
    )

    try:
        # Authenticate user
        user = user_service.authenticate_user(login_data.email, login_data.password)

        # Create tokens
        access_token = create_access_token(
            user_id=user.id,
            company_id=user.company_id
        )

        refresh_token = create_refresh_token(
            user_id=user.id,
            company_id=user.company_id
        )

        logger.info(f"Login successful for user: {user.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=86400  # 1 day in seconds
        )

    except Exception as e:
        logger.error(f"Login failed for {login_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    **No authentication required** - uses refresh token instead.

    When your access token expires (after 1 day), use this endpoint
    to get a new access token without requiring the user to log in again.

    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/auth/refresh" \\
      -H "Content-Type: application/json" \\
      -d '{"refresh_token": "your-refresh-token-here"}'
    ```
    """
    try:
        # Verify refresh token
        payload = verify_refresh_token(refresh_data.refresh_token)

        user_id = payload.get("sub")
        company_id = payload.get("company_id")

        if not user_id or not company_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Verify user still exists and is active
        user_repo = UserRepository(db)
        from uuid import UUID
        user = user_repo.get_by_id(UUID(user_id))

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Create new tokens
        new_access_token = create_access_token(
            user_id=user.id,
            company_id=user.company_id
        )

        new_refresh_token = create_refresh_token(
            user_id=user.id,
            company_id=user.company_id
        )

        logger.info(f"Token refreshed for user: {user.email}")

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=86400
        )

    except InvalidTokenError as e:
        logger.warning(f"Invalid refresh token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


@router.post("/setup/request-link", response_model=SetupLinkResponse)
async def request_setup_link(
    request_data: SetupLinkRequest,
):
    """
    Request a magic link for company setup.

    Returns the same response regardless of whether the email is authorized,
    to prevent email enumeration.
    """
    email = request_data.email.lower()
    allowed_emails = [e.lower() for e in settings.SETUP_ALLOWED_EMAILS]

    if email in allowed_emails:
        token = create_setup_token(email)
        setup_url = f"{settings.FRONTEND_URL}/setup/create?token={token}"

        email_service = EmailService()
        await email_service.send_setup_magic_link_email(
            to=email,
            setup_url=setup_url,
            company_name=settings.COMPANY_NAME
        )
        logger.info(f"Setup magic link sent to {email}")
    else:
        logger.info(f"Setup link requested for unauthorized email: {email}")

    return SetupLinkResponse()


@router.get("/setup/verify", response_model=SetupTokenVerifyResponse)
def verify_setup_token_endpoint(
    token: str,
):
    """
    Verify a setup token from a magic link.

    Returns whether the token is valid and the associated email.
    """
    try:
        payload = verify_setup_token(token)
        return SetupTokenVerifyResponse(valid=True, email=payload.get("sub"))
    except InvalidTokenError:
        return SetupTokenVerifyResponse(valid=False)


@router.post("/setup", response_model=CompanySetupResponse, status_code=status.HTTP_201_CREATED)
def setup_company(
    setup_data: CompanySetupRequest,
    db: Session = Depends(get_db)
):
    """
    Initial company setup endpoint.

    Creates the first company and admin user in one operation.
    Requires a valid setup token from the magic link flow.
    """
    logger.info(f"Company setup initiated for: {setup_data.company_name}")

    try:
        # Validate setup token
        payload = verify_setup_token(setup_data.setup_token)
        logger.info(f"Setup token verified for email: {payload.get('sub')}")
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired setup token"
        )

    try:
        # Initialize repositories
        company_repo = CompanyRepository(db)
        user_repo = UserRepository(db)
        role_repo = RoleRepository(db)

        # Initialize services
        company_service = CompanyService(repository=company_repo)
        user_service = UserService(
            user_repository=user_repo,
            company_repository=company_repo,
            role_repository=role_repo,
            password_hasher=password_hasher
        )
        role_service = RoleService(
            role_repository=role_repo,
            company_repository=company_repo
        )

        # Create company
        from app.schemas.company import CompanyCreate
        company_data = CompanyCreate(
            name=setup_data.company_name,
            email=setup_data.company_email,
            phone=setup_data.company_phone,
            address=setup_data.company_address
        )
        company = company_service.create_company(company_data)

        # Create admin role for the company
        from app.schemas.role import RoleCreate
        admin_role_data = RoleCreate(
            name="Admin",
            description="Administrator role with full permissions",
            company_id=company.id,
            is_active=True
        )
        admin_role = role_service.create_role(admin_role_data)

        # Create admin user
        from app.schemas.user import UserCreate
        admin_user_data = UserCreate(
            email=setup_data.admin_email,
            username=setup_data.admin_username,
            password=setup_data.admin_password,
            first_name=setup_data.admin_first_name,
            last_name=setup_data.admin_last_name,
            phone=setup_data.admin_phone,
            company_id=company.id,
            role_ids=[admin_role.id]
        )
        # Set as superuser
        admin_user = user_service.create_user(admin_user_data)
        user_repo.update(admin_user, is_superuser=True)

        # Commit transaction
        db.commit()

        logger.info(f"Company setup completed: {company.name} (ID: {company.id})")

        return CompanySetupResponse(
            company_id=company.id,
            company_name=company.name,
            admin_user_id=admin_user.id,
            admin_email=admin_user.email,
            message="Company and admin user created successfully. You can now login with the admin credentials."
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Company setup failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company setup failed: {str(e)}"
        )
