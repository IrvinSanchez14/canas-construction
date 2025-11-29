"""Project Category Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models import ProjectCategory
from app.repositories.base import BaseRepository


class ProjectCategoryRepository(BaseRepository[ProjectCategory]):
    """Repository for ProjectCategory entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(ProjectCategory, db)

    def get_by_company(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> List[ProjectCategory]:
        """
        Get all project categories for a specific company.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit
            active_only: Filter only active categories
        """
        query = self.db.query(ProjectCategory).filter(
            ProjectCategory.company_id == company_id
        )

        if active_only:
            query = query.filter(ProjectCategory.is_active == True)

        return query.offset(skip).limit(limit).all()

    def get_by_name(self, name: str, company_id: UUID) -> Optional[ProjectCategory]:
        """Get project category by name within a company."""
        return self.db.query(ProjectCategory).filter(
            ProjectCategory.name == name,
            ProjectCategory.company_id == company_id
        ).first()

    def exists_by_name(
        self,
        name: str,
        company_id: UUID,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """Check if category name exists within a company."""
        query = self.db.query(ProjectCategory.id).filter(
            ProjectCategory.name == name,
            ProjectCategory.company_id == company_id
        )

        if exclude_id:
            query = query.filter(ProjectCategory.id != exclude_id)

        return query.first() is not None

    def get_active_categories(self, company_id: UUID) -> List[ProjectCategory]:
        """Get all active categories for a company."""
        return self.db.query(ProjectCategory).filter(
            ProjectCategory.company_id == company_id,
            ProjectCategory.is_active == True
        ).all()

    def count_by_company(self, company_id: UUID) -> int:
        """Count project categories for a specific company."""
        return self.count(filters={"company_id": company_id})
