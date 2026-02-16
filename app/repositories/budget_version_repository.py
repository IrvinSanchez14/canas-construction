"""BudgetVersion Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.models.budget_version import BudgetVersion
from app.repositories.base import BaseRepository


class BudgetVersionRepository(BaseRepository[BudgetVersion]):
    """Repository for BudgetVersion entity."""

    def __init__(self, db: Session):
        super().__init__(BudgetVersion, db)

    def get_by_budget(
        self,
        budget_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[BudgetVersion]:
        """Get all versions for a budget ordered by version number descending."""
        return (
            self.db.query(BudgetVersion)
            .options(joinedload(BudgetVersion.created_by))
            .filter(BudgetVersion.budget_id == budget_id)
            .order_by(BudgetVersion.version_number.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_latest_version_number(self, budget_id: UUID) -> int:
        """Get the latest version number for a budget."""
        result = (
            self.db.query(BudgetVersion.version_number)
            .filter(BudgetVersion.budget_id == budget_id)
            .order_by(BudgetVersion.version_number.desc())
            .first()
        )
        return result[0] if result else 0

    def count_by_budget(self, budget_id: UUID) -> int:
        """Count total versions for a budget."""
        return (
            self.db.query(BudgetVersion)
            .filter(BudgetVersion.budget_id == budget_id)
            .count()
        )

    def get_by_id_with_details(self, version_id: UUID) -> Optional[BudgetVersion]:
        """Get version by ID with creator eagerly loaded."""
        return (
            self.db.query(BudgetVersion)
            .options(joinedload(BudgetVersion.created_by))
            .filter(BudgetVersion.id == version_id)
            .first()
        )
