"""
Visit Service following SOLID principles.

Business logic for Visit management:
- Dependency injection
- Multi-tenant isolation
- Validation
- Transaction management
- Audit trail tracking
"""

from typing import List, Optional
from datetime import date
from uuid import UUID
from decimal import Decimal

from app.models import Visit, VisitStatus
from app.repositories import VisitRepository, ProjectRepository, UserRepository
from app.schemas.visit import VisitCreate, VisitUpdate
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)


class VisitService:
    """
    Service layer for Visit business logic following SOLID principles.

    Dependencies injected:
    - VisitRepository: Data access
    - ProjectRepository: Project validation and multi-tenant isolation
    - UserRepository: User validation for audit trail
    """

    def __init__(
        self,
        visit_repository: VisitRepository,
        project_repository: ProjectRepository,
        user_repository: UserRepository
    ):
        """Initialize service with all dependencies injected."""
        self.visit_repository = visit_repository
        self.project_repository = project_repository
        self.user_repository = user_repository

    def create_visit(
        self,
        visit_data: VisitCreate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None,
        send_client_notification: bool = False
    ) -> Visit:
        """
        Create a new visit.

        Business Rules:
        - Project must exist and belong to the company
        - Creator user must exist and belong to the company
        - Multi-tenant isolation enforced
        - Calculates total cost if materials and labor costs are provided

        Args:
            visit_data: Visit creation data
            company_id: Company ID for multi-tenant validation
            created_by_user_id: User ID who is creating this visit (for audit)

        Returns:
            Created visit

        Raises:
            NotFoundException: If project or user not found
            ValidationException: If project/user doesn't belong to company
        """
        # Validate project exists and belongs to company
        project = self.project_repository.get_by_id(visit_data.project_id)
        if not project:
            logger.error(f"Project not found: {visit_data.project_id}")
            raise NotFoundException(f"Project with ID {visit_data.project_id} not found")

        # Validate project belongs to company (multi-tenant)
        if project.client.company_id != company_id:
            logger.warning(
                f"Multi-tenant violation: User from company {company_id} "
                f"trying to access project from company {project.client.company_id}"
            )
            raise ValidationException("Project does not belong to your company")

        # Validate creator user if provided
        if created_by_user_id:
            creator = self.user_repository.get_by_id(created_by_user_id)
            if not creator:
                logger.error(f"Creator user not found: {created_by_user_id}")
                raise NotFoundException(f"User with ID {created_by_user_id} not found")

            if creator.company_id != company_id:
                logger.warning(
                    f"Multi-tenant violation: Creator from company {creator.company_id} "
                    f"doesn't match company {company_id}"
                )
                raise ValidationException("Creator user does not belong to your company")
        else:
            created_by_user_id = None

        # Calculate total estimated cost
        estimated_total_cost = None
        if visit_data.estimated_materials_cost and visit_data.estimated_labor_cost:
            estimated_total_cost = visit_data.estimated_materials_cost + visit_data.estimated_labor_cost

        # Create visit
        visit = self.visit_repository.create(
            title=visit_data.title,
            description=visit_data.description,
            status=visit_data.status,
            visit_date=visit_data.visit_date,
            visit_time=visit_data.visit_time,
            inspection_notes=visit_data.inspection_notes,
            estimated_materials_cost=visit_data.estimated_materials_cost,
            estimated_labor_cost=visit_data.estimated_labor_cost,
            estimated_total_cost=estimated_total_cost,
            images=visit_data.images,
            attachments=visit_data.attachments,
            visit_items=visit_data.visit_items,
            project_id=visit_data.project_id,
            created_by_user_id=created_by_user_id
        )

        logger.info(f"Created visit {visit.id} for project {visit_data.project_id}")

        # Send notification
        try:
            from app.core.notifications import send_notification_background
            import threading

            threading.Thread(
                target=send_notification_background,
                args=(
                    self.visit_repository.db,
                    "visit.created",
                    "Visit",
                    visit.id,
                    visit.title,
                    company_id,
                    None,
                    {
                        "Project": project.name,
                        "Status": visit.status.value,
                        "Date": str(visit.visit_date) if visit.visit_date else "N/A",
                        "Time": str(visit.visit_time) if visit.visit_time else "N/A",
                    }
                ),
                daemon=True
            ).start()
        except Exception as e:
            logger.error(f"Failed to queue notification: {str(e)}")

        # Send email notification to the project's client if requested
        if send_client_notification and project.client and project.client.email:
            try:
                from app.services.email_service import EmailService
                import asyncio

                client = project.client
                email_service = EmailService()
                details = {
                    "Project": project.name,
                    "Visit Date": str(visit.visit_date) if visit.visit_date else "To be determined",
                    "Visit Time": str(visit.visit_time) if visit.visit_time else "To be determined",
                    "Status": visit.status.value.replace("_", " ").title(),
                }

                def _send_client_email():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(
                            email_service.send_entity_created_email(
                                to=[client.email],
                                entity_type="Visit",
                                entity_name=visit.title,
                                created_at=str(visit.created_at),
                                details=details,
                            )
                        )
                    finally:
                        loop.close()

                threading.Thread(target=_send_client_email, daemon=True).start()
                logger.info(f"Queued client notification email to {client.email} for visit {visit.id}")
            except Exception as e:
                logger.error(f"Failed to queue client notification email: {str(e)}")

        return visit

    def get_visit(self, visit_id: UUID, company_id: UUID) -> Visit:
        """
        Get a visit by ID with multi-tenant validation.

        Args:
            visit_id: Visit ID
            company_id: Company ID for validation

        Returns:
            Visit with details

        Raises:
            NotFoundException: If visit not found
            ValidationException: If visit doesn't belong to company
        """
        visit = self.visit_repository.get_by_id_with_details(visit_id)
        if not visit:
            logger.error(f"Visit not found: {visit_id}")
            raise NotFoundException(f"Visit with ID {visit_id} not found")

        # Validate project belongs to company (multi-tenant)
        if visit.project.client.company_id != company_id:
            logger.warning(
                f"Multi-tenant violation: User from company {company_id} "
                f"trying to access visit from company {visit.project.client.company_id}"
            )
            raise ValidationException("Visit does not belong to your company")

        return visit

    def get_visits(
        self,
        company_id: UUID,
        project_id: Optional[UUID] = None,
        status: Optional[VisitStatus] = None,
        skip: int = 0,
        limit: int = 100,
        include_details: bool = True,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Visit]:
        """
        Get visits with optional filters and multi-tenant isolation.

        Args:
            company_id: Company ID for multi-tenant validation
            project_id: Optional project filter
            status: Optional status filter
            skip: Pagination offset
            limit: Pagination limit
            include_details: Whether to include relationship details

        Returns:
            List of visits
        """
        if project_id:
            # Validate project belongs to company
            project = self.project_repository.get_by_id(project_id)
            if not project:
                raise NotFoundException(f"Project with ID {project_id} not found")

            if project.client.company_id != company_id:
                logger.warning(
                    f"Multi-tenant violation: User from company {company_id} "
                    f"trying to access project from company {project.client.company_id}"
                )
                raise ValidationException("Project does not belong to your company")

            return self.visit_repository.get_by_project(
                project_id=project_id,
                skip=skip,
                limit=limit,
                status=status,
                include_details=include_details
            )

        # Get by status across all company projects (or all visits if no status filter)
        return self.visit_repository.get_all_by_company(
            company_id=company_id,
            skip=skip,
            limit=limit,
            status=status,
            date_from=date_from,
            date_to=date_to,
            include_details=include_details
        )

    def update_visit(
        self,
        visit_id: UUID,
        visit_data: VisitUpdate,
        company_id: UUID,
        edited_by_user_id: Optional[UUID] = None
    ) -> Visit:
        """
        Update a visit.

        Args:
            visit_id: Visit ID
            visit_data: Update data
            company_id: Company ID for validation
            edited_by_user_id: User ID who is editing this visit (for audit)

        Returns:
            Updated visit

        Raises:
            NotFoundException: If visit not found
            ValidationException: If visit doesn't belong to company
        """
        visit = self.get_visit(visit_id, company_id)

        # Validate editor user if provided
        if edited_by_user_id:
            editor = self.user_repository.get_by_id(edited_by_user_id)
            if not editor:
                raise NotFoundException(f"User with ID {edited_by_user_id} not found")

            if editor.company_id != company_id:
                raise ValidationException("Editor user does not belong to your company")

        # Update fields
        update_dict = visit_data.model_dump(exclude_unset=True, exclude={"edited_by_user_id"})

        # Recalculate total cost if cost fields are updated
        if "estimated_materials_cost" in update_dict or "estimated_labor_cost" in update_dict:
            materials = update_dict.get("estimated_materials_cost", visit.estimated_materials_cost)
            labor = update_dict.get("estimated_labor_cost", visit.estimated_labor_cost)
            if materials and labor:
                update_dict["estimated_total_cost"] = materials + labor

        # Update visit
        for key, value in update_dict.items():
            setattr(visit, key, value)

        if edited_by_user_id:
            visit.edited_by_user_id = edited_by_user_id

        self.visit_repository.db.flush()
        self.visit_repository.db.refresh(visit)

        logger.info(f"Updated visit {visit_id}")

        # Send notification
        try:
            from app.core.notifications import send_notification_background
            import threading

            threading.Thread(
                target=send_notification_background,
                args=(
                    self.visit_repository.db,
                    "visit.updated",
                    "Visit",
                    visit.id,
                    visit.title,
                    company_id,
                    None,
                    {
                        "Project": visit.project.name if visit.project else "N/A",
                        "Status": visit.status.value,
                        "Date": str(visit.visit_date) if visit.visit_date else "N/A",
                        "Time": str(visit.visit_time) if visit.visit_time else "N/A",
                    }
                ),
                daemon=True
            ).start()
        except Exception as e:
            logger.error(f"Failed to queue notification: {str(e)}")

        return visit

    def delete_visit(self, visit_id: UUID, company_id: UUID) -> bool:
        """
        Delete a visit with multi-tenant validation.

        Args:
            visit_id: Visit ID
            company_id: Company ID for validation

        Returns:
            True if deleted

        Raises:
            NotFoundException: If visit not found
            ValidationException: If visit doesn't belong to company
        """
        visit = self.get_visit(visit_id, company_id)
        self.visit_repository.delete(visit_id)
        logger.info(f"Deleted visit {visit_id}")
        return True

    def change_visit_status(
        self,
        visit_id: UUID,
        new_status: VisitStatus,
        company_id: UUID,
        reviewed_by_user_id: Optional[UUID] = None
    ) -> Visit:
        """
        Change visit status (workflow management).

        Typical workflow:
        - PLANNING: Initial data collection
        - IN_REVIEW: Engineering reviewing the data
        - INSPECTION_REQUIRED: Additional inspection needed
        - APPROVED: Approved for planning phase
        - VISITED: Visit completed

        Args:
            visit_id: Visit ID
            new_status: New status
            company_id: Company ID for validation
            reviewed_by_user_id: User ID who reviewed/approved (for audit)

        Returns:
            Updated visit
        """
        visit = self.get_visit(visit_id, company_id)

        # Update status
        visit.status = new_status

        # Update review timestamp if status is IN_REVIEW or APPROVED
        if new_status in [VisitStatus.IN_REVIEW, VisitStatus.APPROVED]:
            from datetime import datetime
            visit.reviewed_at = datetime.utcnow()

        if reviewed_by_user_id:
            visit.edited_by_user_id = reviewed_by_user_id

        self.visit_repository.db.flush()
        self.visit_repository.db.refresh(visit)

        logger.info(f"Changed visit {visit_id} status to {new_status}")
        return visit

    def get_pending_reviews(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Visit]:
        """
        Get visits pending engineering review.

        Returns visits in PLANNING or INSPECTION_REQUIRED status.
        """
        visits = self.visit_repository.get_pending_review(skip=skip, limit=limit)
        # Filter by company (multi-tenant safety check)
        return [v for v in visits if v.project.client.company_id == company_id]

    def get_project_visits_summary(self, project_id: UUID, company_id: UUID) -> dict:
        """Get summary statistics for a project's visits."""
        project = self.project_repository.get_by_id(project_id)
        if not project:
            raise NotFoundException(f"Project with ID {project_id} not found")

        if project.client.company_id != company_id:
            raise ValidationException("Project does not belong to your company")

        total_visits = self.visit_repository.count_by_project(project_id)
        visits_by_status = {}
        for status in VisitStatus:
            visits_by_status[status.value] = self.visit_repository.db.query(Visit).filter(
                Visit.project_id == project_id,
                Visit.status == status
            ).count()

        return {
            "project_id": project_id,
            "total_visits": total_visits,
            "visits_by_status": visits_by_status
        }
