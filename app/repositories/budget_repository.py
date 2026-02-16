"""Budget Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from uuid import UUID
from decimal import Decimal

from app.models import Budget, BudgetItem, BudgetStatus
from app.models.budget_category import BudgetCategory
from app.models.category_profit import CategoryProfit
from app.repositories.base import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    """Repository for Budget entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(Budget, db)

    def get_by_id_with_details(self, budget_id: UUID, include_categories: bool = True) -> Optional[Budget]:
        """Get budget by ID with categories, items, and visit eagerly loaded."""
        from app.models.visit import Visit
        from app.models.project import Project

        query = self.db.query(Budget).options(
            joinedload(Budget.visit).joinedload(Visit.project).joinedload(Project.client),
            joinedload(Budget.accepted_by)
        )

        if include_categories:
            query = query.options(
                joinedload(Budget.budget_categories)
                .joinedload(BudgetCategory.budget_items)
                .joinedload(BudgetItem.catalog_item),
                joinedload(Budget.budget_categories)
                .joinedload(BudgetCategory.category_profit)
            )

        return query.filter(Budget.id == budget_id).first()

    def get_by_visit(self, visit_id: UUID, include_categories: bool = True) -> Optional[Budget]:
        """Get budget for a specific visit."""
        query = self.db.query(Budget).filter(Budget.visit_id == visit_id)

        if include_categories:
            query = query.options(
                joinedload(Budget.budget_categories)
                .joinedload(BudgetCategory.budget_items)
                .joinedload(BudgetItem.catalog_item),
                joinedload(Budget.budget_categories)
                .joinedload(BudgetCategory.category_profit),
                joinedload(Budget.accepted_by)
            )

        return query.first()

    def get_by_status(
        self,
        status: BudgetStatus,
        skip: int = 0,
        limit: int = 100,
        include_categories: bool = False
    ) -> List[Budget]:
        """Get all budgets with a specific status."""
        query = self.db.query(Budget).filter(Budget.status == status)

        if include_categories:
            query = query.options(
                joinedload(Budget.budget_categories)
                .joinedload(BudgetCategory.budget_items)
                .joinedload(BudgetItem.catalog_item)
            )

        return query.offset(skip).limit(limit).all()

    def count_by_status(self, status: BudgetStatus) -> int:
        """Count total budgets with a specific status."""
        return self.db.query(Budget).filter(Budget.status == status).count()

    def get_all_by_company(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[BudgetStatus] = None,
        include_categories: bool = True
    ) -> List[Budget]:
        """Get all budgets for a company by joining through visits -> projects -> clients."""
        from app.models.visit import Visit
        from app.models.project import Project
        from app.models.client import Client

        query = (
            self.db.query(Budget)
            .join(Budget.visit)
            .join(Visit.project)
            .join(Project.client)
            .filter(Client.company_id == company_id)
        )

        if status:
            query = query.filter(Budget.status == status)

        if include_categories:
            query = query.options(
                joinedload(Budget.budget_categories)
                .joinedload(BudgetCategory.budget_items)
                .joinedload(BudgetItem.catalog_item),
                joinedload(Budget.budget_categories)
                .joinedload(BudgetCategory.category_profit),
                joinedload(Budget.visit).joinedload(Visit.project),
                joinedload(Budget.accepted_by)
            )

        return query.order_by(Budget.created_at.desc()).offset(skip).limit(limit).all()

    def recalculate_total(self, budget_id: UUID) -> Decimal:
        """Recalculate total amount from budget categories' subtotals."""
        total = self.db.query(
            func.coalesce(func.sum(BudgetCategory.subtotal), 0)
        ).filter(
            BudgetCategory.budget_id == budget_id
        ).scalar()

        return Decimal(str(total)) if total else Decimal('0')


class BudgetItemRepository(BaseRepository[BudgetItem]):
    """Repository for BudgetItem entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(BudgetItem, db)

    def get_by_category(
        self,
        category_id: UUID,
        include_catalog: bool = True
    ) -> List[BudgetItem]:
        """Get all items for a specific category."""
        query = self.db.query(BudgetItem).filter(BudgetItem.budget_category_id == category_id)

        if include_catalog:
            query = query.options(joinedload(BudgetItem.catalog_item))

        return query.order_by(BudgetItem.order_index).all()

    def get_by_id_with_catalog(self, item_id: UUID) -> Optional[BudgetItem]:
        """Get budget item by ID with catalog item eagerly loaded."""
        return (
            self.db.query(BudgetItem)
            .options(joinedload(BudgetItem.catalog_item))
            .filter(BudgetItem.id == item_id)
            .first()
        )

    def delete_by_category(self, category_id: UUID) -> int:
        """Delete all items for a category (returns count deleted)."""
        count = self.db.query(BudgetItem).filter(BudgetItem.budget_category_id == category_id).delete()
        self.db.flush()
        return count
