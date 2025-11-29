"""
Improved User Service following SOLID principles.

Major improvements:
- Dependency injection (repositories, password hasher)
- No static methods
- Proper logging
- Custom exceptions
- Transaction management delegated to repository
- N+1 query optimization via repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import User, Role
from app.repositories import UserRepository, CompanyRepository, RoleRepository
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    ValidationException,
    AuthenticationException
)
from app.core.password import PasswordHasher
from app.core.logging import get_logger

logger = get_logger(__name__)


class UserService:
    """
    Service layer for User business logic following SOLID principles.

    Dependencies injected:
    - UserRepository: Data access
    - CompanyRepository: Company validation
    - RoleRepository: Role validation
    - PasswordHasher: Password operations
    """

    def __init__(
        self,
        user_repository: UserRepository,
        company_repository: CompanyRepository,
        role_repository: RoleRepository,
        password_hasher: PasswordHasher
    ):
        """Initialize service with all dependencies injected."""
        self.user_repository = user_repository
        self.company_repository = company_repository
        self.role_repository = role_repository
        self.password_hasher = password_hasher

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Business Rules:
        - Email must be unique
        - Company must exist
        - All roles must exist and belong to the same company

        Args:
            user_data: User creation data

        Returns:
            Created user

        Raises:
            NotFoundException: If company not found
            AlreadyExistsException: If email exists
            ValidationException: If roles invalid
        """
        logger.info(f"Creating user: {user_data.email}")

        # Validate company exists
        company = self.company_repository.get_by_id_or_fail(user_data.company_id)

        # Validate email is unique
        if self.user_repository.exists_by_email(user_data.email):
            raise AlreadyExistsException("User", "email", user_data.email)

        # Validate and get roles
        roles = []
        if user_data.role_ids:
            roles = self._validate_and_get_roles(user_data.role_ids, user_data.company_id)

        # Hash password
        hashed_password = self.password_hasher.hash(user_data.password)

        # Create user
        user = self.user_repository.create(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            company_id=user_data.company_id
        )

        # Assign roles
        user.roles = roles

        logger.info(f"User created successfully: {user.id}")
        return user

    def get_user(self, user_id: int, company_id: Optional[int] = None) -> User:
        """
        Get user by ID with optional company filter.

        Args:
            user_id: User ID
            company_id: Optional company filter for multi-tenant isolation

        Returns:
            User with roles eagerly loaded

        Raises:
            NotFoundException: If user not found
            ValidationException: If user doesn't belong to company
        """
        user = self.user_repository.get_by_id_with_roles(user_id)

        if not user:
            raise NotFoundException("User", user_id)

        # Validate company ownership if company_id provided
        if company_id is not None and user.company_id != company_id:
            raise ValidationException(
                f"User {user_id} does not belong to company {company_id}"
            )

        return user

    def get_users(
        self,
        company_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[User]:
        """
        Get users with optional filters.

        Args:
            company_id: Filter by company (recommended for multi-tenant)
            skip: Pagination offset
            limit: Pagination limit
            is_active: Filter by active status

        Returns:
            List of users with roles eagerly loaded (N+1 optimized)
        """
        if company_id:
            # Use optimized company-specific method
            users = self.user_repository.get_by_company(
                company_id=company_id,
                skip=skip,
                limit=limit,
                include_roles=True
            )

            # Apply is_active filter if needed
            if is_active is not None:
                users = [u for u in users if u.is_active == is_active]

            return users
        else:
            filters = {}
            if is_active is not None:
                filters["is_active"] = is_active

            return self.user_repository.get_all(skip=skip, limit=limit, filters=filters)

    def update_user(
        self,
        user_id: int,
        user_data: UserUpdate,
        company_id: Optional[int] = None
    ) -> User:
        """
        Update user.

        Business Rules:
        - Email must remain unique (if changed)
        - Roles must belong to user's company

        Args:
            user_id: User ID
            user_data: Update data
            company_id: Optional company filter

        Returns:
            Updated user

        Raises:
            NotFoundException: If user not found
            AlreadyExistsException: If email conflict
            ValidationException: If roles invalid
        """
        logger.info(f"Updating user: {user_id}")

        # Get user
        user = self.get_user(user_id, company_id)

        update_data = user_data.model_dump(exclude_unset=True)

        # Handle password update
        if "password" in update_data:
            update_data["hashed_password"] = self.password_hasher.hash(update_data["password"])
            del update_data["password"]

        # Handle role updates
        if "role_ids" in update_data:
            role_ids = update_data.pop("role_ids")
            if role_ids is not None:
                roles = self._validate_and_get_roles(role_ids, user.company_id)
                user.roles = roles

        # Validate email uniqueness
        if "email" in update_data and update_data["email"] != user.email:
            if self.user_repository.exists_by_email(update_data["email"]):
                raise AlreadyExistsException("User", "email", update_data["email"])

        # Update user
        updated_user = self.user_repository.update(user, **update_data)
        logger.info(f"User updated successfully: {user_id}")

        return updated_user

    def delete_user(self, user_id: int, company_id: Optional[int] = None) -> None:
        """
        Delete user.

        Args:
            user_id: User ID
            company_id: Optional company filter

        Raises:
            NotFoundException: If user not found
        """
        logger.warning(f"Deleting user: {user_id}")

        user = self.get_user(user_id, company_id)
        self.user_repository.delete(user)

        logger.info(f"User deleted successfully: {user_id}")

    def authenticate_user(self, email: str, password: str) -> User:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: Plain password

        Returns:
            Authenticated user

        Raises:
            AuthenticationException: If authentication fails
        """
        user = self.user_repository.get_by_email(email)

        if not user:
            logger.warning(f"Authentication failed: user not found - {email}")
            raise AuthenticationException()

        if not self.password_hasher.verify(password, user.hashed_password):
            logger.warning(f"Authentication failed: invalid password - {email}")
            raise AuthenticationException()

        if not user.is_active:
            logger.warning(f"Authentication failed: user inactive - {email}")
            raise AuthenticationException("User account is inactive")

        logger.info(f"User authenticated successfully: {email}")
        return user

    def _validate_and_get_roles(self, role_ids: List[int], company_id: int) -> List[Role]:
        """
        Validate roles exist and belong to company.

        Private method - business logic helper.

        Args:
            role_ids: List of role IDs
            company_id: Company ID

        Returns:
            List of validated roles

        Raises:
            ValidationException: If roles invalid
        """
        roles = []
        for role_id in role_ids:
            role = self.role_repository.get_by_id(role_id)

            if not role:
                raise ValidationException(f"Role {role_id} not found")

            if role.company_id != company_id:
                raise ValidationException(
                    f"Role {role_id} does not belong to company {company_id}"
                )

            roles.append(role)

        return roles
