"""
Project Service following SOLID principles.

Business logic for Project management:
- Dependency injection
- Multi-tenant isolation
- Validation
- Transaction management
"""

from typing import List, Optional
from datetime import date
from uuid import UUID

from app.models import Project, ProjectStatus
from app.repositories import (
    ProjectRepository,
    ClientRepository,
    ProjectCategoryRepository,
    UserRepository
)
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.core.exceptions import (
    NotFoundException,
    ValidationException
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProjectService:
    """
    Service layer for Project business logic following SOLID principles.

    Dependencies injected:
    - ProjectRepository: Data access
    - ClientRepository: Client validation
    - ProjectCategoryRepository: Category validation
    - UserRepository: User validation for creator tracking
    """

    def __init__(
        self,
        project_repository: ProjectRepository,
        client_repository: ClientRepository,
        project_category_repository: ProjectCategoryRepository,
        user_repository: UserRepository
    ):
        """Initialize service with all dependencies injected."""
        self.project_repository = project_repository
        self.client_repository = client_repository
        self.project_category_repository = project_category_repository
        self.user_repository = user_repository

    def create_project(
        self,
        project_data: ProjectCreate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> Project:
        """
        Create a new project.

        Business Rules:
        - Client must exist and belong to the company
        - Category must exist and belong to the company
        - Creator user must exist and belong to the company
        - Multi-tenant isolation enforced

        Args:
            project_data: Project creation data
            company_id: Company ID for multi-tenant validation
            created_by_user_id: User ID who is creating this project (for audit)

        Returns:
            Created project

        Raises:
            NotFoundException: If client, category, or user not found
            ValidationException: If client, category, or user doesn't belong to company
        """
        logger.info(f"Creating project: {project_data.name} for company {company_id}")

        # Validate client exists and belongs to company
        client = self.client_repository.get_by_id(project_data.client_id)
        if not client:
            raise NotFoundException("Client", project_data.client_id)

        if client.company_id != company_id:
            raise ValidationException(
                f"Client {project_data.client_id} does not belong to company {company_id}"
            )

        # Validate category exists and belongs to company
        category = self.project_category_repository.get_by_id(project_data.category_id)
        if not category:
            raise NotFoundException("ProjectCategory", project_data.category_id)

        if category.company_id != company_id:
            raise ValidationException(
                f"ProjectCategory {project_data.category_id} does not belong to company {company_id}"
            )

        # Use provided creator or fallback to project_data
        creator_id = created_by_user_id or project_data.created_by_user_id

        # Validate creator user if provided
        if creator_id:
            user = self.user_repository.get_by_id(creator_id)
            if not user:
                raise NotFoundException("User", creator_id)

            # Validate user belongs to the company
            if user.company_id != company_id:
                raise ValidationException(
                    f"User {creator_id} does not belong to company {company_id}"
                )

        # Create project
        project = self.project_repository.create(
            name=project_data.name,
            description=project_data.description,
            status=project_data.status,
            start_date=project_data.start_date,
            address=project_data.address,
            client_id=project_data.client_id,
            category_id=project_data.category_id,
            created_by_user_id=creator_id
        )

        logger.info(f"Project created successfully: {project.id}")
        
        # Send notification
        try:
            from app.core.notifications import send_notification_background
            import threading
            
            threading.Thread(
                target=send_notification_background,
                args=(
                    self.project_repository.db,
                    "project.created",
                    "Project",
                    project.id,
                    project.name,
                    company_id,
                    None,  # created_by
                    {
                        "Client": client.name,
                        "Status": project.status.value,
                        "Location": project.address if project.address else "N/A"
                    }
                ),
                daemon=True
            ).start()
        except Exception as e:
            logger.error(f"Failed to queue notification: {str(e)}")
        
        return project

    def get_project(
        self,
        project_id: UUID,
        company_id: Optional[UUID] = None,
        include_details: bool = True
    ) -> Project:
        """
        Get project by ID with optional company filter.

        Args:
            project_id: Project ID
            company_id: Optional company filter for multi-tenant isolation
            include_details: Whether to include client and category details

        Returns:
            Project with details eagerly loaded

        Raises:
            NotFoundException: If project not found
            ValidationException: If project's client doesn't belong to company
        """
        if include_details:
            project = self.project_repository.get_by_id_with_details(project_id)
        else:
            project = self.project_repository.get_by_id(project_id)

        if not project:
            raise NotFoundException("Project", project_id)

        # Validate company ownership if company_id provided
        if company_id is not None:
            if not project.client:
                # Load client if not loaded
                client = self.client_repository.get_by_id(project.client_id)
            else:
                client = project.client

            if client.company_id != company_id:
                raise ValidationException(
                    f"Project {project_id} does not belong to company {company_id}"
                )

        return project

    def get_projects(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ProjectStatus] = None,
        category_id: Optional[UUID] = None,
        client_id: Optional[UUID] = None,
        include_details: bool = True,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Project]:
        """
        Get projects for a company with optional filters.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit
            status: Optional status filter
            category_id: Optional category filter
            client_id: Optional client filter
            include_details: Whether to include details (N+1 optimized)
            date_from: Filter projects created on or after this date
            date_to: Filter projects created on or before this date

        Returns:
            List of projects
        """
        if client_id:
            # Filter by client
            return self.project_repository.get_by_client(
                client_id=client_id,
                skip=skip,
                limit=limit,
                include_details=include_details
            )
        else:
            # Filter by company
            return self.project_repository.get_by_company(
                company_id=company_id,
                skip=skip,
                limit=limit,
                status=status,
                category_id=category_id,
                date_from=date_from,
                date_to=date_to,
                include_details=include_details
            )

    def update_project(
        self,
        project_id: UUID,
        project_data: ProjectUpdate,
        company_id: Optional[UUID] = None
    ) -> Project:
        """
        Update project.

        Business Rules:
        - If changing category, new category must belong to same company

        Args:
            project_id: Project ID
            project_data: Update data
            company_id: Optional company filter

        Returns:
            Updated project

        Raises:
            NotFoundException: If project or category not found
            ValidationException: If validation fails
        """
        logger.info(f"Updating project: {project_id}")

        # Get project
        project = self.get_project(project_id, company_id, include_details=False)

        update_data = project_data.model_dump(exclude_unset=True)

        # Validate new category if changing
        if "category_id" in update_data:
            category = self.project_category_repository.get_by_id(update_data["category_id"])
            if not category:
                raise NotFoundException("ProjectCategory", update_data["category_id"])

            # Get client to validate company
            client = self.client_repository.get_by_id(project.client_id)
            if category.company_id != client.company_id:
                raise ValidationException(
                    f"ProjectCategory {update_data['category_id']} does not belong to the same company as the project's client"
                )

        # Update project
        updated_project = self.project_repository.update(project, **update_data)
        logger.info(f"Project updated successfully: {project_id}")

        return updated_project

    def delete_project(
        self,
        project_id: UUID,
        company_id: Optional[UUID] = None
    ) -> None:
        """
        Delete project.

        Args:
            project_id: Project ID
            company_id: Optional company filter

        Raises:
            NotFoundException: If project not found
        """
        logger.warning(f"Deleting project: {project_id}")

        project = self.get_project(project_id, company_id, include_details=False)
        self.project_repository.delete(project)

        logger.info(f"Project deleted successfully: {project_id}")

    def count_projects(self, company_id: UUID) -> int:
        """Count projects for a company."""
        return self.project_repository.count_by_company(company_id)

    def count_projects_by_status(self, company_id: UUID, status: ProjectStatus) -> int:
        """Count projects by status for a company."""
        return self.project_repository.count_by_status(company_id, status)

    def get_projects_by_status(
        self,
        company_id: UUID,
        status: ProjectStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Project]:
        """Get projects by status for a company."""
        return self.project_repository.get_by_status(
            status=status,
            company_id=company_id,
            skip=skip,
            limit=limit
        )
