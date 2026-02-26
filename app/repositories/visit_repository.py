"""Visit Repository - Data Access Layer."""

from typing import List, Optional
from datetime import date, datetime, time
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.models import Visit, VisitStatus
from app.repositories.base import BaseRepository


class VisitRepository(BaseRepository[Visit]):
    """Repository for Visit entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(Visit, db)

    def get_by_id_with_details(self, visit_id: UUID, include_creators: bool = True) -> Optional[Visit]:
        """Get visit by ID with project and user details eagerly loaded (N+1 optimization)."""
        query = self.db.query(Visit).options(
            joinedload(Visit.project)
        )

        if include_creators:
            query = query.options(
                joinedload(Visit.created_by),
                joinedload(Visit.edited_by)
            )

        return query.filter(Visit.id == visit_id).first()

    def get_by_project(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[VisitStatus] = None,
        include_details: bool = True,
        include_creators: bool = True
    ) -> List[Visit]:
        """
        Get all visits for a specific project.

        Args:
            project_id: Project ID filter
            skip: Pagination offset
            limit: Pagination limit
            status: Optional status filter
            include_details: Whether to eager load project details
            include_creators: Whether to eager load creator and editor users
        """
        query = self.db.query(Visit).filter(Visit.project_id == project_id)

        if status:
            query = query.filter(Visit.status == status)

        if include_details:
            query = query.options(joinedload(Visit.project))

        if include_creators:
            query = query.options(
                joinedload(Visit.created_by),
                joinedload(Visit.edited_by)
            )

        return query.offset(skip).limit(limit).all()

    def get_by_status(
        self,
        status: VisitStatus,
        skip: int = 0,
        limit: int = 100,
        include_details: bool = True
    ) -> List[Visit]:
        """Get all visits with a specific status."""
        query = self.db.query(Visit).filter(Visit.status == status)

        if include_details:
            query = query.options(
                joinedload(Visit.project),
                joinedload(Visit.created_by),
                joinedload(Visit.edited_by)
            )

        return query.offset(skip).limit(limit).all()

    def get_recent_by_project(
        self,
        project_id: UUID,
        limit: int = 10
    ) -> List[Visit]:
        """Get most recent visits for a project."""
        return (
            self.db.query(Visit)
            .filter(Visit.project_id == project_id)
            .order_by(Visit.created_at.desc())
            .options(
                joinedload(Visit.created_by),
                joinedload(Visit.edited_by)
            )
            .limit(limit)
            .all()
        )

    def count_by_project(self, project_id: UUID) -> int:
        """Count total visits for a project."""
        return self.db.query(Visit).filter(Visit.project_id == project_id).count()

    def count_by_status(self, status: VisitStatus) -> int:
        """Count total visits with a specific status."""
        return self.db.query(Visit).filter(Visit.status == status).count()

    def get_pending_review(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Visit]:
        """Get visits pending for engineering review (planning and inspection_required)."""
        return (
            self.db.query(Visit)
            .filter(
                Visit.status.in_([VisitStatus.PLANNING, VisitStatus.INSPECTION_REQUIRED])
            )
            .order_by(Visit.created_at.asc())
            .options(
                joinedload(Visit.project),
                joinedload(Visit.created_by)
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_by_company(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[VisitStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        include_details: bool = True,
        include_creators: bool = True
    ) -> List[Visit]:
        """
        Get all visits for a company by joining through projects to clients.

        Args:
            company_id: Company ID to filter by
            skip: Pagination offset
            limit: Pagination limit
            status: Optional status filter
            date_from: Filter visits created on or after this date
            date_to: Filter visits created on or before this date
            include_details: Whether to eager load project details
            include_creators: Whether to eager load creator and editor users
        """
        from app.models import Project, Client

        query = (
            self.db.query(Visit)
            .join(Visit.project)
            .join(Project.client)
            .filter(Client.company_id == company_id)
        )

        if status:
            query = query.filter(Visit.status == status)

        if date_from:
            query = query.filter(Visit.created_at >= datetime.combine(date_from, time.min))
        if date_to:
            query = query.filter(Visit.created_at <= datetime.combine(date_to, time.max))

        if include_details:
            query = query.options(joinedload(Visit.project))

        if include_creators:
            query = query.options(
                joinedload(Visit.created_by),
                joinedload(Visit.edited_by)
            )

        return query.order_by(Visit.created_at.desc()).offset(skip).limit(limit).all()
