"""
Client Service following SOLID principles.

Business logic for Client management:
- Dependency injection
- Multi-tenant isolation
- Validation
- Transaction management
"""

from typing import List, Optional
from uuid import UUID

from app.models import Client
from app.repositories import ClientRepository, CompanyRepository
from app.schemas.client import ClientCreate, ClientUpdate
from app.core.exceptions import (
    NotFoundException,
    ValidationException
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ClientService:
    """
    Service layer for Client business logic following SOLID principles.

    Dependencies injected:
    - ClientRepository: Data access
    - CompanyRepository: Company validation
    """

    def __init__(
        self,
        client_repository: ClientRepository,
        company_repository: CompanyRepository
    ):
        """Initialize service with all dependencies injected."""
        self.client_repository = client_repository
        self.company_repository = company_repository

    def create_client(self, client_data: ClientCreate) -> Client:
        """
        Create a new client.

        Business Rules:
        - Company must exist
        - Client belongs to a company (multi-tenant)

        Args:
            client_data: Client creation data

        Returns:
            Created client

        Raises:
            NotFoundException: If company not found
        """
        logger.info(f"Creating client: {client_data.name} for company {client_data.company_id}")

        # Validate company exists
        self.company_repository.get_by_id_or_fail(client_data.company_id)

        # Create client
        client = self.client_repository.create(
            name=client_data.name,
            email=client_data.email,
            phone=client_data.phone,
            company_id=client_data.company_id
        )

        logger.info(f"Client created successfully: {client.id}")
        return client

    def get_client(self, client_id: UUID, company_id: Optional[UUID] = None) -> Client:
        """
        Get client by ID with optional company filter for multi-tenant isolation.

        Args:
            client_id: Client ID
            company_id: Optional company filter

        Returns:
            Client with projects eagerly loaded

        Raises:
            NotFoundException: If client not found
            ValidationException: If client doesn't belong to company
        """
        client = self.client_repository.get_by_id_with_projects(client_id)

        if not client:
            raise NotFoundException("Client", client_id)

        # Validate company ownership if company_id provided
        if company_id is not None and client.company_id != company_id:
            raise ValidationException(
                f"Client {client_id} does not belong to company {company_id}"
            )

        return client

    def get_clients(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_projects: bool = False
    ) -> List[Client]:
        """
        Get clients for a company.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit
            include_projects: Whether to include projects (N+1 optimized)

        Returns:
            List of clients
        """
        return self.client_repository.get_by_company(
            company_id=company_id,
            skip=skip,
            limit=limit,
            include_projects=include_projects
        )

    def update_client(
        self,
        client_id: UUID,
        client_data: ClientUpdate,
        company_id: Optional[UUID] = None
    ) -> Client:
        """
        Update client.

        Args:
            client_id: Client ID
            client_data: Update data
            company_id: Optional company filter

        Returns:
            Updated client

        Raises:
            NotFoundException: If client not found
            ValidationException: If client doesn't belong to company
        """
        logger.info(f"Updating client: {client_id}")

        # Get client
        client = self.get_client(client_id, company_id)

        update_data = client_data.model_dump(exclude_unset=True)

        # Update client
        updated_client = self.client_repository.update(client, **update_data)
        logger.info(f"Client updated successfully: {client_id}")

        return updated_client

    def delete_client(self, client_id: UUID, company_id: Optional[UUID] = None) -> None:
        """
        Delete client.

        Args:
            client_id: Client ID
            company_id: Optional company filter

        Raises:
            NotFoundException: If client not found
        """
        logger.warning(f"Deleting client: {client_id}")

        client = self.get_client(client_id, company_id)
        self.client_repository.delete(client)

        logger.info(f"Client deleted successfully: {client_id}")

    def count_clients(self, company_id: UUID) -> int:
        """Count clients for a company."""
        return self.client_repository.count_by_company(company_id)
