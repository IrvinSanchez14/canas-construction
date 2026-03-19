"""Change Order Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from uuid import UUID
from decimal import Decimal

from app.models.change_order import ChangeOrder, ChangeOrderItem
from app.repositories.base import BaseRepository


class ChangeOrderRepository(BaseRepository[ChangeOrder]):
    """Repository for ChangeOrder entity."""

    def __init__(self, db: Session):
        super().__init__(ChangeOrder, db)

    def get_by_id_with_details(self, change_order_id: UUID) -> Optional[ChangeOrder]:
        """Get change order by ID with items and relationships eagerly loaded."""
        from app.models.project import Project

        return (
            self.db.query(ChangeOrder)
            .options(
                joinedload(ChangeOrder.change_order_items),
                joinedload(ChangeOrder.project)
                .joinedload(Project.client),
                joinedload(ChangeOrder.accepted_by),
                joinedload(ChangeOrder.applied_by),
                joinedload(ChangeOrder.created_by),
            )
            .filter(ChangeOrder.id == change_order_id)
            .first()
        )

    def get_by_project(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChangeOrder]:
        """Get all change orders for a project."""
        return (
            self.db.query(ChangeOrder)
            .options(
                joinedload(ChangeOrder.change_order_items),
                joinedload(ChangeOrder.accepted_by),
                joinedload(ChangeOrder.applied_by),
                joinedload(ChangeOrder.created_by),
            )
            .filter(ChangeOrder.project_id == project_id)
            .order_by(ChangeOrder.order_number.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_project(self, project_id: UUID) -> int:
        """Count change orders for a project."""
        return (
            self.db.query(ChangeOrder)
            .filter(ChangeOrder.project_id == project_id)
            .count()
        )

    def get_next_order_number(self, project_id: UUID) -> int:
        """Get the next order number for a project's change orders."""
        result = (
            self.db.query(func.coalesce(func.max(ChangeOrder.order_number), 0))
            .filter(ChangeOrder.project_id == project_id)
            .scalar()
        )
        return result + 1

    def recalculate_total(self, change_order_id: UUID) -> Decimal:
        """Recalculate total amount from items."""
        total = self.db.query(
            func.coalesce(func.sum(ChangeOrderItem.subtotal), 0)
        ).filter(
            ChangeOrderItem.change_order_id == change_order_id
        ).scalar()

        return Decimal(str(total)) if total else Decimal('0')

    def get_all_by_company(
        self,
        company_id: UUID,
        project_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChangeOrder]:
        """Get all change orders for a company."""
        from app.models.project import Project
        from app.models.client import Client

        query = (
            self.db.query(ChangeOrder)
            .join(ChangeOrder.project)
            .join(Project.client)
            .filter(Client.company_id == company_id)
        )

        if project_id:
            query = query.filter(ChangeOrder.project_id == project_id)

        if status:
            query = query.filter(ChangeOrder.status == status)

        query = query.options(
            joinedload(ChangeOrder.change_order_items),
            joinedload(ChangeOrder.project)
            .joinedload(Project.client),
            joinedload(ChangeOrder.accepted_by),
            joinedload(ChangeOrder.applied_by),
            joinedload(ChangeOrder.created_by),
        )

        return query.order_by(ChangeOrder.created_at.desc()).offset(skip).limit(limit).all()

    def count_by_company(
        self,
        company_id: UUID,
        project_id: Optional[UUID] = None,
        status: Optional[str] = None
    ) -> int:
        """Count change orders for a company."""
        from app.models.project import Project
        from app.models.client import Client

        query = (
            self.db.query(ChangeOrder)
            .join(ChangeOrder.project)
            .join(Project.client)
            .filter(Client.company_id == company_id)
        )

        if project_id:
            query = query.filter(ChangeOrder.project_id == project_id)

        if status:
            query = query.filter(ChangeOrder.status == status)

        return query.count()


class ChangeOrderItemRepository(BaseRepository[ChangeOrderItem]):
    """Repository for ChangeOrderItem entity."""

    def __init__(self, db: Session):
        super().__init__(ChangeOrderItem, db)

    def get_by_change_order(self, change_order_id: UUID) -> List[ChangeOrderItem]:
        """Get all items for a change order ordered by order_index."""
        return (
            self.db.query(ChangeOrderItem)
            .filter(ChangeOrderItem.change_order_id == change_order_id)
            .order_by(ChangeOrderItem.order_index)
            .all()
        )

    def delete_by_change_order(self, change_order_id: UUID) -> int:
        """Delete all items for a change order."""
        count = (
            self.db.query(ChangeOrderItem)
            .filter(ChangeOrderItem.change_order_id == change_order_id)
            .delete()
        )
        self.db.flush()
        return count
