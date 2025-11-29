"""
Improved Role Service following SOLID principles.

Changes from original:
- Dependency injection (repositories)
- Proper logging
- Custom exceptions
- Business logic only
"""

from typing import List, Optional

from app.models import Role
from app.repositories import RoleRepository, CompanyRepository
from app.schemas.role import RoleCreate, RoleUpdate
from app.core.exceptions import NotFoundException, AlreadyExistsException, ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)


class RoleService:
    """
    Service layer for Role business logic following SOLID principles.

    Dependencies injected:
    - RoleRepository: Data access
    - CompanyRepository: Company validation
    """

    def __init__(
        self,
        role_repository: RoleRepository,
        company_repository: CompanyRepository
    ):
        """Initialize service with injected dependencies."""
        self.role_repository = role_repository
        self.company_repository = company_repository

    def create_role(self, role_data: RoleCreate) -> Role:
        """
        Create a new role for a company.

        Business Rules:
        - Company must exist
        - Role name must be unique within company

        Args:
            role_data: Role creation data

        Returns:
            Created role

        Raises:
            NotFoundException: If company not found
            AlreadyExistsException: If role name exists in company
        """
        logger.info(f"Creating role '{role_data.name}' for company {role_data.company_id}")

        # Validate company exists
        self.company_repository.get_by_id_or_fail(role_data.company_id)

        # Validate role name is unique within company
        if self.role_repository.exists_in_company(role_data.name, role_data.company_id):
            raise AlreadyExistsException(
                "Role",
                "name",
                f"{role_data.name} in company {role_data.company_id}"
            )

        # Create role
        role = self.role_repository.create(
            name=role_data.name,
            description=role_data.description,
            company_id=role_data.company_id
        )

        logger.info(f"Role created successfully: {role.id}")
        return role

    def get_role(self, role_id: int, company_id: Optional[int] = None) -> Role:
        """
        Get role by ID with optional company filter.

        Args:
            role_id: Role ID
            company_id: Optional company filter for multi-tenant isolation

        Returns:
            Role

        Raises:
            NotFoundException: If role not found
            ValidationException: If role doesn't belong to company
        """
        role = self.role_repository.get_by_id(role_id)

        if not role:
            raise NotFoundException("Role", role_id)

        # Validate company ownership if company_id provided
        if company_id is not None and role.company_id != company_id:
            raise ValidationException(
                f"Role {role_id} does not belong to company {company_id}"
            )

        return role

    def get_roles(
        self,
        company_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[Role]:
        """
        Get roles with optional filters.

        Args:
            company_id: Filter by company (recommended for multi-tenant)
            skip: Pagination offset
            limit: Pagination limit
            is_active: Filter by active status

        Returns:
            List of roles
        """
        if company_id:
            roles = self.role_repository.get_by_company(
                company_id=company_id,
                skip=skip,
                limit=limit
            )

            # Apply is_active filter if needed
            if is_active is not None:
                roles = [r for r in roles if r.is_active == is_active]

            return roles
        else:
            filters = {}
            if is_active is not None:
                filters["is_active"] = is_active

            return self.role_repository.get_all(skip=skip, limit=limit, filters=filters)

    def update_role(
        self,
        role_id: int,
        role_data: RoleUpdate,
        company_id: Optional[int] = None
    ) -> Role:
        """
        Update role.

        Business Rules:
        - Role name must remain unique within company (if changed)

        Args:
            role_id: Role ID
            role_data: Update data
            company_id: Optional company filter

        Returns:
            Updated role

        Raises:
            NotFoundException: If role not found
            AlreadyExistsException: If name conflict
        """
        logger.info(f"Updating role: {role_id}")

        # Get role
        role = self.get_role(role_id, company_id)

        update_data = role_data.model_dump(exclude_unset=True)

        # Validate name uniqueness if changing name
        if "name" in update_data and update_data["name"] != role.name:
            if self.role_repository.exists_in_company(
                update_data["name"],
                role.company_id,
                exclude_id=role_id
            ):
                raise AlreadyExistsException(
                    "Role",
                    "name",
                    f"{update_data['name']} in company {role.company_id}"
                )

        # Update role
        updated_role = self.role_repository.update(role, **update_data)
        logger.info(f"Role updated successfully: {role_id}")

        return updated_role

    def delete_role(self, role_id: int, company_id: Optional[int] = None) -> None:
        """
        Delete role.

        Args:
            role_id: Role ID
            company_id: Optional company filter

        Raises:
            NotFoundException: If role not found
        """
        logger.warning(f"Deleting role: {role_id}")

        role = self.get_role(role_id, company_id)
        self.role_repository.delete(role)

        logger.info(f"Role deleted successfully: {role_id}")

    def get_active_roles_by_company(self, company_id: int) -> List[Role]:
        """
        Get all active roles for a company.

        Args:
            company_id: Company ID

        Returns:
            List of active roles
        """
        return self.role_repository.get_active_roles_by_company(company_id)
