"""Reference Repository - Data Access Layer."""

from typing import List
from sqlalchemy.orm import Session
from uuid import UUID

from app.models import Reference
from app.repositories.base import BaseRepository


class ReferenceRepository(BaseRepository[Reference]):
    """Repository for Reference entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(Reference, db)

    def get_by_company(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Reference]:
        """
        Get all references for a specific company ordered by display_order.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit
        """
        return self.db.query(Reference).filter(
            Reference.company_id == company_id
        ).order_by(Reference.display_order).offset(skip).limit(limit).all()

    def count_by_company(self, company_id: UUID) -> int:
        """Count references for a specific company."""
        return self.count(filters={"company_id": company_id})
