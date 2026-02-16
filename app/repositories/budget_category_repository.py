"""BudgetCategory Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from uuid import UUID
from decimal import Decimal

from app.models.budget_category import BudgetCategory
from app.models.budget import BudgetItem
from app.repositories.base import BaseRepository


class BudgetCategoryRepository(BaseRepository[BudgetCategory]):
    """Repository for BudgetCategory entity."""

    def __init__(self, db: Session):
        super().__init__(BudgetCategory, db)

    def get_by_id_with_items(self, category_id: UUID) -> Optional[BudgetCategory]:
        """Get category by ID with items eagerly loaded."""
        return (
            self.db.query(BudgetCategory)
            .options(
                joinedload(BudgetCategory.budget_items).joinedload(BudgetItem.catalog_item)
            )
            .filter(BudgetCategory.id == category_id)
            .first()
        )

    def get_by_budget(self, budget_id: UUID, include_items: bool = True) -> List[BudgetCategory]:
        """Get all categories for a budget ordered by order_index."""
        query = self.db.query(BudgetCategory).filter(BudgetCategory.budget_id == budget_id)

        if include_items:
            query = query.options(
                joinedload(BudgetCategory.budget_items).joinedload(BudgetItem.catalog_item)
            )

        return query.order_by(BudgetCategory.order_index).all()

    def recalculate_subtotal(self, category_id: UUID) -> Decimal:
        """Recalculate category subtotal from its items."""
        total = self.db.query(
            func.coalesce(func.sum(BudgetItem.subtotal), 0)
        ).filter(
            BudgetItem.budget_category_id == category_id
        ).scalar()

        return Decimal(str(total)) if total else Decimal('0')
