"""CategoryProfit Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.models.category_profit import CategoryProfit
from app.repositories.base import BaseRepository


class CategoryProfitRepository(BaseRepository[CategoryProfit]):
    """Repository for CategoryProfit entity."""

    def __init__(self, db: Session):
        super().__init__(CategoryProfit, db)

    def get_by_budget_category(self, budget_category_id: UUID) -> Optional[CategoryProfit]:
        """Get profit data for a specific budget category (one-to-one)."""
        return (
            self.db.query(CategoryProfit)
            .options(joinedload(CategoryProfit.created_by))
            .filter(CategoryProfit.budget_category_id == budget_category_id)
            .first()
        )

    def get_all_by_budget(self, budget_id: UUID) -> List[CategoryProfit]:
        """Get all profit records for categories in a budget."""
        from app.models.budget_category import BudgetCategory
        return (
            self.db.query(CategoryProfit)
            .join(CategoryProfit.budget_category)
            .options(joinedload(CategoryProfit.created_by))
            .filter(BudgetCategory.budget_id == budget_id)
            .all()
        )

    def get_by_id_with_details(self, profit_id: UUID) -> Optional[CategoryProfit]:
        """Get profit by ID with creator eagerly loaded."""
        return (
            self.db.query(CategoryProfit)
            .options(joinedload(CategoryProfit.created_by))
            .filter(CategoryProfit.id == profit_id)
            .first()
        )
