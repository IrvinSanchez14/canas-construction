"""
Budget Service following SOLID principles.

Business logic for Budget management:
- Dependency injection
- Multi-tenant isolation
- Validation
- Transaction management
- Budget acceptance workflow (updates project status)
"""

from typing import List, Optional, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from app.models import Budget, BudgetItem, BudgetStatus, ProjectStatus
from app.repositories import (
    BudgetRepository,
    BudgetItemRepository,
    VisitRepository,
    ProjectRepository,
    UserRepository,
    CatalogItemRepository
)
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetItemCreate, BudgetItemUpdate
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)


class BudgetService:
    """
    Service layer for Budget business logic following SOLID principles.

    Dependencies injected:
    - BudgetRepository: Data access
    - BudgetItemRepository: Budget item data access
    - VisitRepository: Visit validation and multi-tenant isolation
    - ProjectRepository: Project status updates
    - UserRepository: User validation for audit trail
    - CatalogItemRepository: Catalog item validation
    """

    def __init__(
        self,
        budget_repository: BudgetRepository,
        budget_item_repository: BudgetItemRepository,
        visit_repository: VisitRepository,
        project_repository: ProjectRepository,
        user_repository: UserRepository,
        catalog_item_repository: CatalogItemRepository
    ):
        """Initialize service with all dependencies injected."""
        self.budget_repository = budget_repository
        self.budget_item_repository = budget_item_repository
        self.visit_repository = visit_repository
        self.project_repository = project_repository
        self.user_repository = user_repository
        self.catalog_item_repository = catalog_item_repository

    def create_budget(
        self,
        budget_data: BudgetCreate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> Budget:
        """
        Create a new budget for a visit.

        Business Rules:
        - Visit must exist and belong to the company
        - Visit must not already have a budget (one-to-one relationship)
        - Catalog items (if referenced) must exist and belong to the company
        - Total amount is calculated from items
        - Items are created with the budget

        Args:
            budget_data: Budget creation data
            company_id: Company ID for multi-tenant validation
            created_by_user_id: User ID who is creating this budget (for audit)

        Returns:
            Created budget with items

        Raises:
            NotFoundException: If visit, catalog item, or user not found
            ValidationException: If validation fails
        """
        # Validate visit exists and belongs to company
        visit = self.visit_repository.get_by_id_with_details(budget_data.visit_id)
        if not visit:
            logger.error(f"Visit not found: {budget_data.visit_id}")
            raise NotFoundException(f"Visit with ID {budget_data.visit_id} not found")

        # Validate visit belongs to company (multi-tenant)
        if visit.project.client.company_id != company_id:
            logger.warning(
                f"Multi-tenant violation: User from company {company_id} "
                f"trying to access visit from company {visit.project.client.company_id}"
            )
            raise ValidationException("Visit does not belong to your company")

        # Check if visit already has a budget
        existing_budget = self.budget_repository.get_by_visit(budget_data.visit_id)
        if existing_budget:
            raise ValidationException("Visit already has a budget")

        # Validate creator user if provided
        if created_by_user_id:
            creator = self.user_repository.get_by_id(created_by_user_id)
            if not creator:
                raise NotFoundException(f"User with ID {created_by_user_id} not found")
            if creator.company_id != company_id:
                raise ValidationException("Creator user does not belong to your company")

        # Validate catalog items if referenced
        if budget_data.budget_items:
            for item in budget_data.budget_items:
                if item.catalog_item_id:
                    catalog_item = self.catalog_item_repository.get_by_id(item.catalog_item_id)
                    if not catalog_item:
                        raise NotFoundException(f"CatalogItem with ID {item.catalog_item_id} not found")
                    if catalog_item.company_id != company_id:
                        raise ValidationException(
                            f"CatalogItem {item.catalog_item_id} does not belong to your company"
                        )

        # Calculate total from items
        total_amount = sum(
            (item.subtotal or (item.quantity * item.unit_price))
            for item in budget_data.budget_items
        )

        # Create budget
        budget = self.budget_repository.create(
            title=budget_data.title,
            description=budget_data.description,
            status=budget_data.status,
            total_amount=total_amount,
            visit_id=budget_data.visit_id
        )

        # Create budget items
        if budget_data.budget_items:
            for idx, item_data in enumerate(budget_data.budget_items):
                subtotal = item_data.subtotal or (item_data.quantity * item_data.unit_price)
                self.budget_item_repository.create(
                    section_name=item_data.section_name,
                    description=item_data.description,
                    unit=item_data.unit,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    subtotal=subtotal,
                    order_index=item_data.order_index or idx,
                    catalog_item_id=item_data.catalog_item_id,
                    budget_id=budget.id
                )

        # Recalculate total to ensure accuracy
        budget.total_amount = self.budget_repository.recalculate_total(budget.id)
        self.budget_repository.db.flush()
        self.budget_repository.db.refresh(budget)

        logger.info(f"Created budget {budget.id} for visit {budget_data.visit_id}")
        return budget

    def get_budget(self, budget_id: UUID, company_id: UUID) -> Budget:
        """
        Get a budget by ID with multi-tenant validation.

        Args:
            budget_id: Budget ID
            company_id: Company ID for validation

        Returns:
            Budget with details

        Raises:
            NotFoundException: If budget not found
            ValidationException: If budget doesn't belong to company
        """
        budget = self.budget_repository.get_by_id_with_details(budget_id, include_items=True)
        if not budget:
            logger.error(f"Budget not found: {budget_id}")
            raise NotFoundException(f"Budget with ID {budget_id} not found")

        # Validate visit belongs to company (multi-tenant)
        visit = budget.visit
        if visit.project.client.company_id != company_id:
            logger.warning(
                f"Multi-tenant violation: User from company {company_id} "
                f"trying to access budget from company {visit.project.client.company_id}"
            )
            raise ValidationException("Budget does not belong to your company")

        return budget

    def get_budgets(
        self,
        company_id: UUID,
        visit_id: Optional[UUID] = None,
        status: Optional[BudgetStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Budget]:
        """
        Get budgets with optional filters and multi-tenant isolation.
        
        Args:
            company_id: Company ID for multi-tenant validation
            visit_id: Optional visit filter
            status: Optional status filter
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            List of budgets
        """
        if visit_id:
            budget = self.get_budget_by_visit(visit_id, company_id)
            return [budget] if budget else []
        
        # Get all budgets for the company
        return self.budget_repository.get_all_by_company(
            company_id=company_id,
            skip=skip,
            limit=limit,
            status=status,
            include_items=True
        )

    def get_budget_by_visit(self, visit_id: UUID, company_id: UUID) -> Optional[Budget]:
        """Get budget for a visit with multi-tenant validation."""
        visit = self.visit_repository.get_by_id_with_details(visit_id)
        if not visit:
            raise NotFoundException(f"Visit with ID {visit_id} not found")

        if visit.project.client.company_id != company_id:
            raise ValidationException("Visit does not belong to your company")

        return self.budget_repository.get_by_visit(visit_id, include_items=True)

    def update_budget(
        self,
        budget_id: UUID,
        budget_data: BudgetUpdate,
        company_id: UUID
    ) -> Budget:
        """
        Update a budget.

        Args:
            budget_id: Budget ID
            budget_data: Update data
            company_id: Company ID for validation

        Returns:
            Updated budget
        """
        budget = self.get_budget(budget_id, company_id)

        update_dict = budget_data.model_dump(exclude_unset=True)
        self.budget_repository.update(budget, **update_dict)

        logger.info(f"Updated budget {budget_id}")
        return budget

    def add_budget_item(
        self,
        budget_id: UUID,
        item_data: BudgetItemCreate,
        company_id: UUID
    ) -> BudgetItem:
        """Add an item to a budget."""
        budget = self.get_budget(budget_id, company_id)

        # Validate catalog item if referenced
        if item_data.catalog_item_id:
            catalog_item = self.catalog_item_repository.get_by_id(item_data.catalog_item_id)
            if not catalog_item:
                raise NotFoundException(f"CatalogItem with ID {item_data.catalog_item_id} not found")
            if catalog_item.company_id != company_id:
                raise ValidationException("CatalogItem does not belong to your company")

        # Calculate subtotal
        subtotal = item_data.subtotal or (item_data.quantity * item_data.unit_price)

        # Get max order_index for this budget
        existing_items = self.budget_item_repository.get_by_budget(budget_id, include_catalog=False)
        max_order = max([item.order_index for item in existing_items], default=-1) if existing_items else -1

        # Create item
        item = self.budget_item_repository.create(
            section_name=item_data.section_name,
            description=item_data.description,
            unit=item_data.unit,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            subtotal=subtotal,
            order_index=item_data.order_index if item_data.order_index is not None else (max_order + 1),
            catalog_item_id=item_data.catalog_item_id,
            budget_id=budget_id
        )

        # Recalculate budget total
        budget.total_amount = self.budget_repository.recalculate_total(budget_id)
        self.budget_repository.db.flush()

        logger.info(f"Added item {item.id} to budget {budget_id}")
        return item

    def update_budget_item(
        self,
        budget_id: UUID,
        item_id: UUID,
        item_data: BudgetItemUpdate,
        company_id: UUID
    ) -> BudgetItem:
        """Update a budget item."""
        budget = self.get_budget(budget_id, company_id)

        item = self.budget_item_repository.get_by_id(item_id)
        if not item or item.budget_id != budget_id:
            raise NotFoundException(f"BudgetItem with ID {item_id} not found in budget {budget_id}")

        # Validate catalog item if being updated
        if item_data.catalog_item_id:
            catalog_item = self.catalog_item_repository.get_by_id(item_data.catalog_item_id)
            if not catalog_item:
                raise NotFoundException(f"CatalogItem with ID {item_data.catalog_item_id} not found")
            if catalog_item.company_id != company_id:
                raise ValidationException("CatalogItem does not belong to your company")

        # Update item
        update_dict = item_data.model_dump(exclude_unset=True)

        # Recalculate subtotal if quantity or unit_price changed
        if "quantity" in update_dict or "unit_price" in update_dict:
            quantity = update_dict.get("quantity", item.quantity)
            unit_price = update_dict.get("unit_price", item.unit_price)
            update_dict["subtotal"] = quantity * unit_price

        self.budget_item_repository.update(item, **update_dict)

        # Recalculate budget total
        budget.total_amount = self.budget_repository.recalculate_total(budget_id)
        self.budget_repository.db.flush()

        logger.info(f"Updated budget item {item_id}")
        return item

    def delete_budget_item(
        self,
        budget_id: UUID,
        item_id: UUID,
        company_id: UUID
    ) -> bool:
        """Delete a budget item."""
        budget = self.get_budget(budget_id, company_id)

        item = self.budget_item_repository.get_by_id(item_id)
        if not item or item.budget_id != budget_id:
            raise NotFoundException(f"BudgetItem with ID {item_id} not found in budget {budget_id}")

        self.budget_item_repository.delete(item)

        # Recalculate budget total
        budget.total_amount = self.budget_repository.recalculate_total(budget_id)
        self.budget_repository.db.flush()

        logger.info(f"Deleted budget item {item_id}")
        return True

    def accept_budget(
        self,
        budget_id: UUID,
        company_id: UUID,
        accepted_by_user_id: UUID
    ) -> Tuple[Budget, "Project"]:
        """
        Accept a budget and update project status.

        Business Rules:
        - Budget must exist and belong to company
        - Budget must be in PENDING_APPROVAL status
        - User must exist and belong to company
        - Project status changes to APPROVED when budget is accepted

        Args:
            budget_id: Budget ID
            company_id: Company ID for validation
            accepted_by_user_id: User ID who is accepting the budget

        Returns:
            Tuple of (updated_budget, updated_project)

        Raises:
            NotFoundException: If budget, project, or user not found
            ValidationException: If validation fails
        """
        budget = self.get_budget(budget_id, company_id)

        # Validate budget status
        if budget.status != BudgetStatus.PENDING_APPROVAL:
            raise ValidationException(
                f"Cannot accept budget with status {budget.status.value}. "
                "Budget must be in PENDING_APPROVAL status."
            )

        # Validate user
        user = self.user_repository.get_by_id(accepted_by_user_id)
        if not user:
            raise NotFoundException(f"User with ID {accepted_by_user_id} not found")
        if user.company_id != company_id:
            raise ValidationException("User does not belong to your company")

        # Update budget
        budget.status = BudgetStatus.ACCEPTED
        budget.accepted_by_user_id = accepted_by_user_id
        budget.accepted_at = datetime.utcnow()

        # Update project status
        project = budget.visit.project
        project.status = ProjectStatus.APPROVED  # Using existing APPROVED status

        self.budget_repository.db.flush()
        self.budget_repository.db.refresh(budget)
        self.project_repository.db.refresh(project)

        logger.info(
            f"Budget {budget_id} accepted by user {accepted_by_user_id}. "
            f"Project {project.id} status changed to APPROVED"
        )

        return budget, project

    def reject_budget(
        self,
        budget_id: UUID,
        company_id: UUID
    ) -> Budget:
        """Reject a budget."""
        budget = self.get_budget(budget_id, company_id)

        if budget.status != BudgetStatus.PENDING_APPROVAL:
            raise ValidationException(
                f"Cannot reject budget with status {budget.status.value}. "
                "Budget must be in PENDING_APPROVAL status."
            )

        budget.status = BudgetStatus.REJECTED
        self.budget_repository.db.flush()
        self.budget_repository.db.refresh(budget)

        logger.info(f"Budget {budget_id} rejected")
        return budget

    def recalculate_budget_total(self, budget_id: UUID, company_id: UUID) -> Budget:
        """Recalculate budget total from items."""
        budget = self.get_budget(budget_id, company_id)
        budget.total_amount = self.budget_repository.recalculate_total(budget_id)
        self.budget_repository.db.flush()
        self.budget_repository.db.refresh(budget)
        return budget
