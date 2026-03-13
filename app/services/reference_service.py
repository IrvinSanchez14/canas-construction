"""
Reference Service following SOLID principles.

Business logic for Reference management:
- Dependency injection
- Multi-tenant isolation
- Validation
- Transaction management
"""

from typing import List, Optional
from uuid import UUID

from app.models import Reference
from app.repositories import ReferenceRepository, CompanyRepository
from app.schemas.reference import ReferenceCreate, ReferenceUpdate
from app.core.exceptions import (
    NotFoundException,
    ValidationException
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReferenceService:
    """
    Service layer for Reference business logic following SOLID principles.

    Dependencies injected:
    - ReferenceRepository: Data access
    - CompanyRepository: Company validation
    """

    def __init__(
        self,
        reference_repository: ReferenceRepository,
        company_repository: CompanyRepository
    ):
        """Initialize service with all dependencies injected."""
        self.reference_repository = reference_repository
        self.company_repository = company_repository

    def create_reference(self, reference_data: ReferenceCreate) -> Reference:
        """
        Create a new reference.

        Business Rules:
        - Company must exist
        - Reference belongs to a company (multi-tenant)

        Args:
            reference_data: Reference creation data

        Returns:
            Created reference

        Raises:
            NotFoundException: If company not found
        """
        logger.info(f"Creating reference: {reference_data.client_name} for company {reference_data.company_id}")

        # Validate company exists
        self.company_repository.get_by_id_or_fail(reference_data.company_id)

        # Create reference
        reference = self.reference_repository.create(
            client_name=reference_data.client_name,
            location=reference_data.location,
            project_description=reference_data.project_description,
            project_value=reference_data.project_value,
            phone=reference_data.phone,
            display_order=reference_data.display_order,
            company_id=reference_data.company_id
        )

        logger.info(f"Reference created successfully: {reference.id}")
        return reference

    def get_reference(self, reference_id: UUID, company_id: Optional[UUID] = None) -> Reference:
        """
        Get reference by ID with optional company filter for multi-tenant isolation.

        Args:
            reference_id: Reference ID
            company_id: Optional company filter

        Returns:
            Reference

        Raises:
            NotFoundException: If reference not found
            ValidationException: If reference doesn't belong to company
        """
        reference = self.reference_repository.get_by_id(reference_id)

        if not reference:
            raise NotFoundException("Reference", reference_id)

        # Validate company ownership if company_id provided
        if company_id is not None and reference.company_id != company_id:
            raise ValidationException(
                f"Reference {reference_id} does not belong to company {company_id}"
            )

        return reference

    def get_references(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Reference]:
        """
        Get references for a company.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of references ordered by display_order
        """
        return self.reference_repository.get_by_company(
            company_id=company_id,
            skip=skip,
            limit=limit
        )

    def update_reference(
        self,
        reference_id: UUID,
        reference_data: ReferenceUpdate,
        company_id: Optional[UUID] = None
    ) -> Reference:
        """
        Update reference.

        Args:
            reference_id: Reference ID
            reference_data: Update data
            company_id: Optional company filter

        Returns:
            Updated reference

        Raises:
            NotFoundException: If reference not found
            ValidationException: If reference doesn't belong to company
        """
        logger.info(f"Updating reference: {reference_id}")

        # Get reference
        reference = self.get_reference(reference_id, company_id)

        update_data = reference_data.model_dump(exclude_unset=True)

        # Update reference
        updated_reference = self.reference_repository.update(reference, **update_data)
        logger.info(f"Reference updated successfully: {reference_id}")

        return updated_reference

    def delete_reference(self, reference_id: UUID, company_id: Optional[UUID] = None) -> None:
        """
        Delete reference.

        Args:
            reference_id: Reference ID
            company_id: Optional company filter

        Raises:
            NotFoundException: If reference not found
        """
        logger.warning(f"Deleting reference: {reference_id}")

        reference = self.get_reference(reference_id, company_id)
        self.reference_repository.delete(reference)

        logger.info(f"Reference deleted successfully: {reference_id}")
