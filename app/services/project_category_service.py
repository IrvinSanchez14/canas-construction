"""
Project Category Service following SOLID principles.

Business logic for ProjectCategory management:
- Dependency injection
- Multi-tenant isolation
- Validation
- Transaction management
"""

from typing import List, Optional
from uuid import UUID

from app.models import ProjectCategory
from app.repositories import ProjectCategoryRepository, CompanyRepository
from app.schemas.project_category import ProjectCategoryCreate, ProjectCategoryUpdate
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    ValidationException
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProjectCategoryService:
    """
    Service layer for ProjectCategory business logic following SOLID principles.

    Dependencies injected:
    - ProjectCategoryRepository: Data access
    - CompanyRepository: Company validation
    """

    def __init__(
        self,
        project_category_repository: ProjectCategoryRepository,
        company_repository: CompanyRepository
    ):
        """Initialize service with all dependencies injected."""
        self.project_category_repository = project_category_repository
        self.company_repository = company_repository

    def create_project_category(self, category_data: ProjectCategoryCreate) -> ProjectCategory:
        """
        Create a new project category.

        Business Rules:
        - Company must exist
        - Category name must be unique within company

        Args:
            category_data: Category creation data

        Returns:
            Created category

        Raises:
            NotFoundException: If company not found
            AlreadyExistsException: If category name exists in company
        """
        logger.info(f"Creating project category: {category_data.name} for company {category_data.company_id}")

        # Validate company exists
        self.company_repository.get_by_id_or_fail(category_data.company_id)

        # Validate category name is unique within company
        if self.project_category_repository.exists_by_name(
            category_data.name,
            category_data.company_id
        ):
            raise AlreadyExistsException(
                "ProjectCategory",
                "name",
                category_data.name
            )

        # Create category
        category = self.project_category_repository.create(
            name=category_data.name,
            description=category_data.description,
            is_active=category_data.is_active,
            company_id=category_data.company_id
        )

        logger.info(f"Project category created successfully: {category.id}")
        return category

    def get_project_category(
        self,
        category_id: UUID,
        company_id: Optional[UUID] = None
    ) -> ProjectCategory:
        """
        Get project category by ID with optional company filter.

        Args:
            category_id: Category ID
            company_id: Optional company filter

        Returns:
            Project category

        Raises:
            NotFoundException: If category not found
            ValidationException: If category doesn't belong to company
        """
        category = self.project_category_repository.get_by_id(category_id)

        if not category:
            raise NotFoundException("ProjectCategory", category_id)

        # Validate company ownership if company_id provided
        if company_id is not None and category.company_id != company_id:
            raise ValidationException(
                f"ProjectCategory {category_id} does not belong to company {company_id}"
            )

        return category

    def get_project_categories(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> List[ProjectCategory]:
        """
        Get project categories for a company.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit
            active_only: Filter only active categories

        Returns:
            List of project categories
        """
        return self.project_category_repository.get_by_company(
            company_id=company_id,
            skip=skip,
            limit=limit,
            active_only=active_only
        )

    def update_project_category(
        self,
        category_id: UUID,
        category_data: ProjectCategoryUpdate,
        company_id: Optional[UUID] = None
    ) -> ProjectCategory:
        """
        Update project category.

        Business Rules:
        - Category name must remain unique within company (if changed)

        Args:
            category_id: Category ID
            category_data: Update data
            company_id: Optional company filter

        Returns:
            Updated category

        Raises:
            NotFoundException: If category not found
            AlreadyExistsException: If name conflict
        """
        logger.info(f"Updating project category: {category_id}")

        # Get category
        category = self.get_project_category(category_id, company_id)

        update_data = category_data.model_dump(exclude_unset=True)

        # Validate name uniqueness if changing name
        if "name" in update_data and update_data["name"] != category.name:
            if self.project_category_repository.exists_by_name(
                update_data["name"],
                category.company_id,
                exclude_id=category_id
            ):
                raise AlreadyExistsException(
                    "ProjectCategory",
                    "name",
                    update_data["name"]
                )

        # Update category
        updated_category = self.project_category_repository.update(category, **update_data)
        logger.info(f"Project category updated successfully: {category_id}")

        return updated_category

    def delete_project_category(
        self,
        category_id: UUID,
        company_id: Optional[UUID] = None
    ) -> None:
        """
        Delete project category.

        Args:
            category_id: Category ID
            company_id: Optional company filter

        Raises:
            NotFoundException: If category not found
        """
        logger.warning(f"Deleting project category: {category_id}")

        category = self.get_project_category(category_id, company_id)
        self.project_category_repository.delete(category)

        logger.info(f"Project category deleted successfully: {category_id}")

    def seed_default_categories(self, company_id: UUID) -> List[ProjectCategory]:
        """
        Seed default project categories for a new company.

        Default categories: Kitchen, Bathroom, Outside, Other

        Args:
            company_id: Company ID

        Returns:
            List of created categories
        """
        logger.info(f"Seeding default categories for company: {company_id}")

        default_categories = [
            {"name": "Kitchen", "description": "Kitchen remodeling and renovation projects"},
            {"name": "Bathroom", "description": "Bathroom remodeling and renovation projects"},
            {"name": "Outside", "description": "Exterior and outdoor construction projects"},
            {"name": "Other", "description": "Miscellaneous construction projects"},
        ]

        created_categories = []
        for cat_data in default_categories:
            # Only create if doesn't exist
            if not self.project_category_repository.exists_by_name(
                cat_data["name"],
                company_id
            ):
                category = self.project_category_repository.create(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    is_active=True,
                    company_id=company_id
                )
                created_categories.append(category)

        logger.info(f"Seeded {len(created_categories)} default categories")
        return created_categories
