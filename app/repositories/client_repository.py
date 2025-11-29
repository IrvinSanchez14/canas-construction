"""Client Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.models import Client
from app.repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    """Repository for Client entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(Client, db)

    def get_by_company(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_projects: bool = False
    ) -> List[Client]:
        """
        Get all clients for a specific company.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit
            include_projects: Whether to eager load projects (prevents N+1)
        """
        query = self.db.query(Client).filter(Client.company_id == company_id)

        if include_projects:
            query = query.options(joinedload(Client.projects))

        return query.offset(skip).limit(limit).all()

    def get_by_id_with_projects(self, client_id: UUID) -> Optional[Client]:
        """Get client by ID with projects eagerly loaded (N+1 optimization)."""
        return self.db.query(Client).options(
            joinedload(Client.projects)
        ).filter(Client.id == client_id).first()

    def get_by_email(self, email: str, company_id: UUID) -> Optional[Client]:
        """Get client by email within a company."""
        return self.db.query(Client).filter(
            Client.email == email,
            Client.company_id == company_id
        ).first()

    def exists_by_name(
        self,
        name: str,
        company_id: UUID,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """Check if client name exists within a company."""
        query = self.db.query(Client.id).filter(
            Client.name == name,
            Client.company_id == company_id
        )

        if exclude_id:
            query = query.filter(Client.id != exclude_id)

        return query.first() is not None

    def count_by_company(self, company_id: UUID) -> int:
        """Count clients for a specific company."""
        return self.count(filters={"company_id": company_id})
