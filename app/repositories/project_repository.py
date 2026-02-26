"""Project Repository - Data Access Layer."""

from typing import List, Optional
from datetime import date, datetime, time
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.models import Project, ProjectStatus
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(Project, db)

    def get_by_id_with_details(self, project_id: UUID, include_creator: bool = True) -> Optional[Project]:
        """Get project by ID with client, category, and creator eagerly loaded (N+1 optimization)."""
        query = self.db.query(Project).options(
            joinedload(Project.client),
            joinedload(Project.category)
        )

        if include_creator:
            query = query.options(joinedload(Project.created_by))

        return query.filter(Project.id == project_id).first()

    def get_by_client(
        self,
        client_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_details: bool = True,
        include_creator: bool = True
    ) -> List[Project]:
        """
        Get all projects for a specific client.

        Args:
            client_id: Client ID filter
            skip: Pagination offset
            limit: Pagination limit
            include_details: Whether to eager load client and category
            include_creator: Whether to eager load creator user
        """
        query = self.db.query(Project).filter(Project.client_id == client_id)

        if include_details:
            query = query.options(
                joinedload(Project.client),
                joinedload(Project.category)
            )

        if include_creator:
            query = query.options(joinedload(Project.created_by))

        return query.offset(skip).limit(limit).all()

    def get_by_company(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ProjectStatus] = None,
        category_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        include_details: bool = True,
        include_creator: bool = True
    ) -> List[Project]:
        """
        Get all projects for a company through client relationship.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit
            status: Optional status filter
            category_id: Optional category filter
            date_from: Filter projects created on or after this date
            date_to: Filter projects created on or before this date
            include_details: Whether to eager load relationships
            include_creator: Whether to eager load creator user
        """
        from app.models import Client

        query = self.db.query(Project).join(Client).filter(
            Client.company_id == company_id
        )

        if status:
            query = query.filter(Project.status == status)

        if category_id:
            query = query.filter(Project.category_id == category_id)

        if date_from:
            query = query.filter(Project.created_at >= datetime.combine(date_from, time.min))
        if date_to:
            query = query.filter(Project.created_at <= datetime.combine(date_to, time.max))

        if include_details:
            query = query.options(
                joinedload(Project.client),
                joinedload(Project.category)
            )

        if include_creator:
            query = query.options(joinedload(Project.created_by))

        return query.offset(skip).limit(limit).all()

    def get_by_status(
        self,
        status: ProjectStatus,
        company_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Project]:
        """Get projects by status, optionally filtered by company."""
        query = self.db.query(Project).filter(Project.status == status)

        if company_id:
            from app.models import Client
            query = query.join(Client).filter(Client.company_id == company_id)

        return query.offset(skip).limit(limit).all()

    def get_by_category(
        self,
        category_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Project]:
        """Get all projects for a specific category."""
        return self.db.query(Project).filter(
            Project.category_id == category_id
        ).offset(skip).limit(limit).all()

    def count_by_company(self, company_id: UUID) -> int:
        """Count projects for a specific company."""
        from app.models import Client

        return self.db.query(Project).join(Client).filter(
            Client.company_id == company_id
        ).count()

    def count_by_status(self, company_id: UUID, status: ProjectStatus) -> int:
        """Count projects by status for a company."""
        from app.models import Client

        return self.db.query(Project).join(Client).filter(
            Client.company_id == company_id,
            Project.status == status
        ).count()
