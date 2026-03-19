"""
Change Order Service following SOLID principles.

Business logic for Change Order management:
- Dependency injection
- Multi-tenant isolation
- Change Order linked to Project
- Apply to budget (finds project's budget, creates new version)
"""

from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from app.models.change_order import ChangeOrder, ChangeOrderItem, ChangeOrderStatus
from app.models.budget import Budget, BudgetStatus
from app.models.budget_category import BudgetCategory
from app.repositories.change_order_repository import ChangeOrderRepository, ChangeOrderItemRepository
from app.repositories import (
    BudgetRepository,
    BudgetCategoryRepository,
    BudgetItemRepository,
    BudgetVersionRepository,
    ProjectRepository,
    UserRepository,
)
from app.schemas.change_order import (
    ChangeOrderCreate,
    ChangeOrderUpdate,
    ChangeOrderItemCreate,
    ChangeOrderItemUpdate,
)
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChangeOrderService:
    """Service layer for Change Order business logic."""

    def __init__(
        self,
        change_order_repository: ChangeOrderRepository,
        change_order_item_repository: ChangeOrderItemRepository,
        budget_repository: BudgetRepository,
        budget_category_repository: BudgetCategoryRepository,
        budget_item_repository: BudgetItemRepository,
        budget_version_repository: BudgetVersionRepository,
        project_repository: ProjectRepository,
        user_repository: UserRepository,
    ):
        self.change_order_repository = change_order_repository
        self.change_order_item_repository = change_order_item_repository
        self.budget_repository = budget_repository
        self.budget_category_repository = budget_category_repository
        self.budget_item_repository = budget_item_repository
        self.budget_version_repository = budget_version_repository
        self.project_repository = project_repository
        self.user_repository = user_repository

    # --- Helpers ---

    def _validate_company(self, change_order: ChangeOrder, company_id: UUID) -> None:
        """Validate change order belongs to company via project→client chain."""
        project = change_order.project
        if project.client.company_id != company_id:
            logger.warning(
                f"Multi-tenant violation: company {company_id} "
                f"trying to access change order from company {project.client.company_id}"
            )
            raise ValidationException("Change order does not belong to your company")

    def _validate_project_company(self, project, company_id: UUID) -> None:
        """Validate project belongs to company."""
        if project.client.company_id != company_id:
            raise ValidationException("Project does not belong to your company")

    def _recalculate_total(self, change_order: ChangeOrder) -> None:
        """Recalculate change order total from items."""
        total = self.change_order_repository.recalculate_total(change_order.id)
        change_order.total_amount = total
        self.change_order_repository.db.flush()

    def _find_project_budget(self, project_id: UUID) -> Optional[Budget]:
        """Find the budget for a project by looking through its visits."""
        from app.models.visit import Visit
        from sqlalchemy.orm import joinedload

        # Query visits for this project that have a budget
        visits = (
            self.change_order_repository.db.query(Visit)
            .filter(Visit.project_id == project_id)
            .all()
        )

        # Find the first visit that has a budget (most recent first)
        for visit in sorted(visits, key=lambda v: v.created_at, reverse=True):
            budget = self.budget_repository.get_by_visit(visit.id, include_categories=True)
            if budget:
                return budget

        return None

    # --- CRUD ---

    def create_change_order(
        self,
        data: ChangeOrderCreate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> ChangeOrder:
        """Create a new change order for a project."""
        # Validate project exists and belongs to company
        project = self.project_repository.get_by_id(data.project_id)
        if not project:
            raise NotFoundException(f"Project with ID {data.project_id} not found")
        self._validate_project_company(project, company_id)

        # Validate creator
        if created_by_user_id:
            user = self.user_repository.get_by_id(created_by_user_id)
            if not user:
                raise NotFoundException(f"User with ID {created_by_user_id} not found")

        # Get next order number
        order_number = self.change_order_repository.get_next_order_number(data.project_id)

        # Create change order
        change_order = self.change_order_repository.create(
            title=data.title,
            description=data.description,
            observations=data.observations,
            order_number=order_number,
            status=data.status,
            project_id=data.project_id,
            created_by_user_id=created_by_user_id,
            total_amount=Decimal('0')
        )

        # Create items
        total = Decimal('0')
        if data.items:
            for idx, item_data in enumerate(data.items):
                subtotal = item_data.subtotal or (
                    Decimal(str(item_data.quantity)) * Decimal(str(item_data.unit_price))
                )
                self.change_order_item_repository.create(
                    change_order_id=change_order.id,
                    item_code=item_data.item_code,
                    description=item_data.description,
                    unit=item_data.unit,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    subtotal=subtotal,
                    order_index=item_data.order_index or idx
                )
                total += subtotal

        # Update total
        change_order.total_amount = total
        self.change_order_repository.db.flush()

        # Reload with details
        return self.change_order_repository.get_by_id_with_details(change_order.id)

    def get_change_order(self, change_order_id: UUID, company_id: UUID) -> ChangeOrder:
        """Get a change order by ID with validation."""
        change_order = self.change_order_repository.get_by_id_with_details(change_order_id)
        if not change_order:
            raise NotFoundException(f"Change order with ID {change_order_id} not found")
        self._validate_company(change_order, company_id)
        return change_order

    def get_change_orders(
        self,
        company_id: UUID,
        project_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple:
        """Get change orders with pagination."""
        change_orders = self.change_order_repository.get_all_by_company(
            company_id=company_id,
            project_id=project_id,
            status=status,
            skip=skip,
            limit=limit
        )
        total = self.change_order_repository.count_by_company(
            company_id=company_id,
            project_id=project_id,
            status=status
        )
        return change_orders, total

    def update_change_order(
        self,
        change_order_id: UUID,
        data: ChangeOrderUpdate,
        company_id: UUID
    ) -> ChangeOrder:
        """Update a change order."""
        change_order = self.get_change_order(change_order_id, company_id)

        if change_order.status in (ChangeOrderStatus.APPLIED,):
            raise ValidationException("Cannot update an applied change order")

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            self.change_order_repository.update(change_order, **update_data)

        return self.change_order_repository.get_by_id_with_details(change_order.id)

    def delete_change_order(
        self,
        change_order_id: UUID,
        company_id: UUID
    ) -> None:
        """Delete a change order."""
        change_order = self.get_change_order(change_order_id, company_id)

        if change_order.status == ChangeOrderStatus.APPLIED:
            raise ValidationException("Cannot delete an applied change order")

        self.change_order_repository.delete(change_order)

    # --- Item Management ---

    def add_item(
        self,
        change_order_id: UUID,
        item_data: ChangeOrderItemCreate,
        company_id: UUID
    ) -> ChangeOrderItem:
        """Add an item to a change order."""
        change_order = self.get_change_order(change_order_id, company_id)

        if change_order.status == ChangeOrderStatus.APPLIED:
            raise ValidationException("Cannot modify an applied change order")

        subtotal = item_data.subtotal or (
            Decimal(str(item_data.quantity)) * Decimal(str(item_data.unit_price))
        )

        item = self.change_order_item_repository.create(
            change_order_id=change_order.id,
            item_code=item_data.item_code,
            description=item_data.description,
            unit=item_data.unit,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            subtotal=subtotal,
            order_index=item_data.order_index
        )

        self._recalculate_total(change_order)
        return item

    def update_item(
        self,
        change_order_id: UUID,
        item_id: UUID,
        item_data: ChangeOrderItemUpdate,
        company_id: UUID
    ) -> ChangeOrderItem:
        """Update a change order item."""
        change_order = self.get_change_order(change_order_id, company_id)

        if change_order.status == ChangeOrderStatus.APPLIED:
            raise ValidationException("Cannot modify an applied change order")

        item = self.change_order_item_repository.get_by_id(item_id)
        if not item or item.change_order_id != change_order.id:
            raise NotFoundException(f"Item with ID {item_id} not found in change order {change_order_id}")

        update_data = item_data.model_dump(exclude_unset=True)

        # Recalculate subtotal if quantity or unit_price changed
        new_quantity = update_data.get('quantity', item.quantity)
        new_unit_price = update_data.get('unit_price', item.unit_price)
        if 'quantity' in update_data or 'unit_price' in update_data:
            update_data['subtotal'] = Decimal(str(new_quantity)) * Decimal(str(new_unit_price))

        self.change_order_item_repository.update(item, **update_data)
        self._recalculate_total(change_order)

        return item

    def delete_item(
        self,
        change_order_id: UUID,
        item_id: UUID,
        company_id: UUID
    ) -> None:
        """Delete a change order item."""
        change_order = self.get_change_order(change_order_id, company_id)

        if change_order.status == ChangeOrderStatus.APPLIED:
            raise ValidationException("Cannot modify an applied change order")

        item = self.change_order_item_repository.get_by_id(item_id)
        if not item or item.change_order_id != change_order.id:
            raise NotFoundException(f"Item with ID {item_id} not found in change order {change_order_id}")

        self.change_order_item_repository.delete(item)
        self._recalculate_total(change_order)

    # --- Workflow ---

    def accept_change_order(
        self,
        change_order_id: UUID,
        company_id: UUID,
        accepted_by_user_id: UUID
    ) -> ChangeOrder:
        """Accept a change order."""
        change_order = self.get_change_order(change_order_id, company_id)

        if change_order.status not in (ChangeOrderStatus.DRAFT, ChangeOrderStatus.PENDING_APPROVAL):
            raise ValidationException(
                f"Cannot accept change order with status '{change_order.status.value}'"
            )

        user = self.user_repository.get_by_id(accepted_by_user_id)
        if not user:
            raise NotFoundException(f"User with ID {accepted_by_user_id} not found")

        change_order.status = ChangeOrderStatus.ACCEPTED
        change_order.accepted_by_user_id = accepted_by_user_id
        change_order.accepted_at = datetime.utcnow()
        self.change_order_repository.db.flush()

        logger.info(f"Change order {change_order_id} accepted by user {accepted_by_user_id}")
        return self.change_order_repository.get_by_id_with_details(change_order.id)

    def reject_change_order(
        self,
        change_order_id: UUID,
        company_id: UUID
    ) -> ChangeOrder:
        """Reject a change order."""
        change_order = self.get_change_order(change_order_id, company_id)

        if change_order.status not in (ChangeOrderStatus.DRAFT, ChangeOrderStatus.PENDING_APPROVAL):
            raise ValidationException(
                f"Cannot reject change order with status '{change_order.status.value}'"
            )

        change_order.status = ChangeOrderStatus.REJECTED
        self.change_order_repository.db.flush()

        logger.info(f"Change order {change_order_id} rejected")
        return self.change_order_repository.get_by_id_with_details(change_order.id)

    def apply_change_order(
        self,
        change_order_id: UUID,
        company_id: UUID,
        applied_by_user_id: UUID
    ) -> ChangeOrder:
        """
        Apply a change order to its project's budget.

        Finds the budget for the project (through visits), adds the change order
        items as a new budget category, and creates a new budget version.
        """
        change_order = self.get_change_order(change_order_id, company_id)

        if change_order.status != ChangeOrderStatus.ACCEPTED:
            raise ValidationException(
                "Change order must be accepted before it can be applied"
            )

        user = self.user_repository.get_by_id(applied_by_user_id)
        if not user:
            raise NotFoundException(f"User with ID {applied_by_user_id} not found")

        # Find the budget for this project
        budget = self._find_project_budget(change_order.project_id)
        if not budget:
            raise ValidationException(
                "No budget found for this project. Create a budget first before applying change orders."
            )

        # 1. Create a budget version snapshot BEFORE applying changes
        self._create_budget_version_snapshot(
            budget,
            applied_by_user_id,
            notes=f"Before applying Change Order #{change_order.order_number}: {change_order.title}"
        )

        # 2. Add change order items as a new budget category
        next_order = max(
            (cat.order_index for cat in budget.budget_categories), default=-1
        ) + 1

        new_category = self.budget_category_repository.create(
            name=f"Change Order #{change_order.order_number} - {change_order.title}",
            description=change_order.description,
            order_index=next_order,
            subtotal=change_order.total_amount,
            budget_id=budget.id
        )

        # 3. Copy items to budget items
        for item in change_order.change_order_items:
            self.budget_item_repository.create(
                description=item.description,
                unit=item.unit,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                order_index=item.order_index,
                budget_category_id=new_category.id
            )

        # 4. Recalculate budget total
        budget.total_amount = self.budget_repository.recalculate_total(budget.id)
        self.budget_repository.db.flush()

        # 5. Mark change order as applied
        change_order.status = ChangeOrderStatus.APPLIED
        change_order.applied_by_user_id = applied_by_user_id
        change_order.applied_at = datetime.utcnow()
        self.change_order_repository.db.flush()

        # 6. Create another version snapshot AFTER applying
        self._create_budget_version_snapshot(
            budget,
            applied_by_user_id,
            notes=f"After applying Change Order #{change_order.order_number}: {change_order.title}"
        )

        logger.info(
            f"Change order {change_order_id} applied to budget {budget.id}, "
            f"new category {new_category.id} created"
        )

        return self.change_order_repository.get_by_id_with_details(change_order.id)

    def _create_budget_version_snapshot(
        self,
        budget: Budget,
        created_by_user_id: Optional[UUID] = None,
        notes: Optional[str] = None
    ) -> None:
        """Create a version snapshot of the budget."""
        next_version = self.budget_version_repository.get_latest_version_number(budget.id) + 1

        categories_snapshot = []
        for cat in budget.budget_categories:
            items_snapshot = []
            for item in cat.budget_items:
                items_snapshot.append({
                    "id": str(item.id),
                    "description": item.description,
                    "unit": item.unit,
                    "quantity": str(item.quantity),
                    "unit_price": str(item.unit_price),
                    "subtotal": str(item.subtotal),
                    "order_index": item.order_index,
                    "catalog_item_id": str(item.catalog_item_id) if item.catalog_item_id else None,
                })
            profit_snapshot = None
            if hasattr(cat, 'category_profit') and cat.category_profit:
                p = cat.category_profit
                profit_snapshot = {
                    "provider_price": str(p.provider_price),
                    "delivery_cost": str(p.delivery_cost),
                    "profit_percentage": str(p.profit_percentage),
                    "total_price": str(p.total_price),
                }
            categories_snapshot.append({
                "id": str(cat.id),
                "name": cat.name,
                "description": cat.description,
                "images": cat.images,
                "order_index": cat.order_index,
                "subtotal": str(cat.subtotal),
                "items": items_snapshot,
                "profit": profit_snapshot,
            })

        snapshot = {
            "title": budget.title,
            "description": budget.description,
            "status": budget.status.value,
            "total_amount": str(budget.total_amount),
            "categories": categories_snapshot,
        }

        self.budget_version_repository.create(
            budget_id=budget.id,
            version_number=next_version,
            snapshot=snapshot,
            notes=notes,
            created_by_user_id=created_by_user_id
        )

        budget.current_version = next_version
        self.budget_repository.db.flush()
