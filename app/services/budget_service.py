"""
Budget Service following SOLID principles.

Business logic for Budget management:
- Dependency injection
- Multi-tenant isolation
- Budget → Categories → Items hierarchy
- Budget versioning (JSON snapshots)
- Budget acceptance workflow (updates project status)
"""

from typing import List, Optional, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime

from app.models import Budget, BudgetItem, BudgetStatus, ProjectStatus
from app.models.budget_category import BudgetCategory
from app.models.budget_version import BudgetVersion
from app.repositories import (
    BudgetRepository,
    BudgetItemRepository,
    BudgetCategoryRepository,
    BudgetVersionRepository,
    VisitRepository,
    ProjectRepository,
    UserRepository,
    CatalogItemRepository
)
from app.repositories.category_profit_repository import CategoryProfitRepository
from app.schemas.budget import (
    BudgetCreate, BudgetUpdate,
    BudgetItemCreate, BudgetItemUpdate,
    BudgetCategoryCreate
)
from app.schemas.budget_category import BudgetCategoryUpdate
from app.schemas.category_profit import CategoryProfitCreate, CategoryProfitUpdate
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)


class BudgetService:
    """Service layer for Budget business logic with categories and versioning."""

    def __init__(
        self,
        budget_repository: BudgetRepository,
        budget_item_repository: BudgetItemRepository,
        budget_category_repository: BudgetCategoryRepository,
        budget_version_repository: BudgetVersionRepository,
        visit_repository: VisitRepository,
        project_repository: ProjectRepository,
        user_repository: UserRepository,
        catalog_item_repository: CatalogItemRepository,
        category_profit_repository: CategoryProfitRepository
    ):
        self.budget_repository = budget_repository
        self.budget_item_repository = budget_item_repository
        self.budget_category_repository = budget_category_repository
        self.budget_version_repository = budget_version_repository
        self.visit_repository = visit_repository
        self.project_repository = project_repository
        self.user_repository = user_repository
        self.catalog_item_repository = catalog_item_repository
        self.category_profit_repository = category_profit_repository

    # --- Helper: Multi-tenant validation ---

    def _validate_budget_company(self, budget: Budget, company_id: UUID) -> None:
        """Validate budget belongs to company via visit→project→client chain."""
        visit = budget.visit
        if visit.project.client.company_id != company_id:
            logger.warning(
                f"Multi-tenant violation: company {company_id} "
                f"trying to access budget from company {visit.project.client.company_id}"
            )
            raise ValidationException("Budget does not belong to your company")

    # --- Helper: Build snapshot for versioning ---

    def _build_snapshot(self, budget: Budget) -> dict:
        """Build a JSON snapshot of the current budget state."""
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

        return {
            "title": budget.title,
            "description": budget.description,
            "status": budget.status.value,
            "total_amount": str(budget.total_amount),
            "categories": categories_snapshot,
        }

    def _create_version_snapshot(
        self,
        budget: Budget,
        created_by_user_id: Optional[UUID] = None,
        notes: Optional[str] = None
    ) -> BudgetVersion:
        """Create a version snapshot of the current budget state."""
        next_version = self.budget_version_repository.get_latest_version_number(budget.id) + 1
        snapshot = self._build_snapshot(budget)

        version = self.budget_version_repository.create(
            budget_id=budget.id,
            version_number=next_version,
            snapshot=snapshot,
            notes=notes,
            created_by_user_id=created_by_user_id
        )

        budget.current_version = next_version
        self.budget_repository.db.flush()

        logger.info(f"Created version {next_version} for budget {budget.id}")
        return version

    # --- Helper: Recalculate totals ---

    def _recalculate_category_and_budget(self, category_id: UUID, budget: Budget) -> None:
        """Recalculate a category subtotal and then the budget total."""
        cat_subtotal = self.budget_category_repository.recalculate_subtotal(category_id)
        category = self.budget_category_repository.get_by_id(category_id)
        if category:
            category.subtotal = cat_subtotal
            self.budget_repository.db.flush()

        budget.total_amount = self.budget_repository.recalculate_total(budget.id)
        self.budget_repository.db.flush()

    # --- Budget CRUD ---

    def create_budget(
        self,
        budget_data: BudgetCreate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> Budget:
        """Create a new budget with categories and items."""
        # Validate visit exists and belongs to company
        visit = self.visit_repository.get_by_id_with_details(budget_data.visit_id)
        if not visit:
            raise NotFoundException(f"Visit with ID {budget_data.visit_id} not found")
        if visit.project.client.company_id != company_id:
            raise ValidationException("Visit does not belong to your company")

        # Check one-to-one constraint
        existing_budget = self.budget_repository.get_by_visit(budget_data.visit_id)
        if existing_budget:
            raise ValidationException("Visit already has a budget")

        # Validate creator
        if created_by_user_id:
            creator = self.user_repository.get_by_id(created_by_user_id)
            if not creator:
                raise NotFoundException(f"User with ID {created_by_user_id} not found")
            if creator.company_id != company_id:
                raise ValidationException("Creator user does not belong to your company")

        # Validate catalog items in all categories
        if budget_data.categories:
            for cat_data in budget_data.categories:
                if cat_data.items:
                    for item in cat_data.items:
                        if item.catalog_item_id:
                            catalog_item = self.catalog_item_repository.get_by_id(item.catalog_item_id)
                            if not catalog_item:
                                raise NotFoundException(f"CatalogItem with ID {item.catalog_item_id} not found")
                            if catalog_item.company_id != company_id:
                                raise ValidationException(f"CatalogItem {item.catalog_item_id} does not belong to your company")

        # Create budget
        budget = self.budget_repository.create(
            title=budget_data.title,
            description=budget_data.description,
            status=budget_data.status,
            total_amount=0,
            current_version=0,
            visit_id=budget_data.visit_id
        )

        # Create categories with items
        budget_total = Decimal('0')
        if budget_data.categories:
            for cat_idx, cat_data in enumerate(budget_data.categories):
                category = self.budget_category_repository.create(
                    name=cat_data.name,
                    description=cat_data.description,
                    images=cat_data.images,
                    order_index=cat_data.order_index if cat_data.order_index else cat_idx,
                    subtotal=0,
                    budget_id=budget.id
                )

                cat_subtotal = Decimal('0')
                if cat_data.items:
                    for item_idx, item_data in enumerate(cat_data.items):
                        subtotal = item_data.subtotal or (item_data.quantity * item_data.unit_price)
                        self.budget_item_repository.create(
                            description=item_data.description,
                            unit=item_data.unit,
                            quantity=item_data.quantity,
                            unit_price=item_data.unit_price,
                            subtotal=subtotal,
                            order_index=item_data.order_index if item_data.order_index else item_idx,
                            catalog_item_id=item_data.catalog_item_id,
                            budget_category_id=category.id
                        )
                        cat_subtotal += subtotal

                category.subtotal = cat_subtotal
                self.budget_repository.db.flush()
                budget_total += cat_subtotal

        budget.total_amount = budget_total
        self.budget_repository.db.flush()
        self.budget_repository.db.refresh(budget)

        logger.info(f"Created budget {budget.id} for visit {budget_data.visit_id}")

        # Send notification
        try:
            from app.core.notifications import send_notification_background
            import threading

            threading.Thread(
                target=send_notification_background,
                args=(
                    self.budget_repository.db,
                    "budget.created",
                    "Budget",
                    budget.id,
                    budget.title,
                    company_id,
                    None,
                    {
                        "Visit": visit.title,
                        "Project": visit.project.name if visit.project else "N/A",
                        "Status": budget.status.value,
                    }
                ),
                daemon=True
            ).start()
        except Exception as e:
            logger.error(f"Failed to queue notification: {str(e)}")

        return budget

    def get_budget(self, budget_id: UUID, company_id: UUID) -> Budget:
        """Get a budget by ID with multi-tenant validation."""
        budget = self.budget_repository.get_by_id_with_details(budget_id, include_categories=True)
        if not budget:
            raise NotFoundException(f"Budget with ID {budget_id} not found")
        self._validate_budget_company(budget, company_id)
        return budget

    def get_budgets(
        self,
        company_id: UUID,
        visit_id: Optional[UUID] = None,
        status: Optional[BudgetStatus] = None,
        skip: int = 0,
        limit: int = 100,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Budget]:
        """Get budgets with optional filters and multi-tenant isolation."""
        if visit_id:
            budget = self.get_budget_by_visit(visit_id, company_id)
            return [budget] if budget else []

        return self.budget_repository.get_all_by_company(
            company_id=company_id,
            skip=skip,
            limit=limit,
            status=status,
            date_from=date_from,
            date_to=date_to,
            include_categories=True
        )

    def get_budget_by_visit(self, visit_id: UUID, company_id: UUID) -> Optional[Budget]:
        """Get budget for a visit with multi-tenant validation."""
        visit = self.visit_repository.get_by_id_with_details(visit_id)
        if not visit:
            raise NotFoundException(f"Visit with ID {visit_id} not found")
        if visit.project.client.company_id != company_id:
            raise ValidationException("Visit does not belong to your company")

        return self.budget_repository.get_by_visit(visit_id, include_categories=True)

    def update_budget(
        self,
        budget_id: UUID,
        budget_data: BudgetUpdate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> Budget:
        """Update a budget. Creates a version snapshot before modifying."""
        budget = self.get_budget(budget_id, company_id)

        # Create version snapshot before modification
        if budget.status != BudgetStatus.DRAFT:
            self._create_version_snapshot(budget, created_by_user_id, notes="Auto-saved before update")

        update_dict = budget_data.model_dump(exclude_unset=True)
        self.budget_repository.update(budget, **update_dict)

        logger.info(f"Updated budget {budget_id}")
        return budget

    # --- Category CRUD ---

    def add_category(
        self,
        budget_id: UUID,
        category_data: BudgetCategoryCreate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> BudgetCategory:
        """Add a category with items to a budget."""
        budget = self.get_budget(budget_id, company_id)

        # Create version snapshot before modification
        if budget.status != BudgetStatus.DRAFT:
            self._create_version_snapshot(budget, created_by_user_id, notes="Auto-saved before adding category")

        # Validate catalog items
        if category_data.items:
            for item in category_data.items:
                if item.catalog_item_id:
                    catalog_item = self.catalog_item_repository.get_by_id(item.catalog_item_id)
                    if not catalog_item:
                        raise NotFoundException(f"CatalogItem with ID {item.catalog_item_id} not found")
                    if catalog_item.company_id != company_id:
                        raise ValidationException(f"CatalogItem {item.catalog_item_id} does not belong to your company")

        # Get max order_index
        existing_categories = self.budget_category_repository.get_by_budget(budget_id, include_items=False)
        max_order = max([c.order_index for c in existing_categories], default=-1) if existing_categories else -1

        category = self.budget_category_repository.create(
            name=category_data.name,
            description=category_data.description,
            images=category_data.images,
            order_index=category_data.order_index if category_data.order_index else (max_order + 1),
            subtotal=0,
            budget_id=budget_id
        )

        cat_subtotal = Decimal('0')
        if category_data.items:
            for item_idx, item_data in enumerate(category_data.items):
                subtotal = item_data.subtotal or (item_data.quantity * item_data.unit_price)
                self.budget_item_repository.create(
                    description=item_data.description,
                    unit=item_data.unit,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    subtotal=subtotal,
                    order_index=item_data.order_index if item_data.order_index else item_idx,
                    catalog_item_id=item_data.catalog_item_id,
                    budget_category_id=category.id
                )
                cat_subtotal += subtotal

        category.subtotal = cat_subtotal
        self.budget_repository.db.flush()

        # Recalculate budget total
        budget.total_amount = self.budget_repository.recalculate_total(budget_id)
        self.budget_repository.db.flush()

        logger.info(f"Added category {category.id} to budget {budget_id}")
        return category

    def update_category(
        self,
        budget_id: UUID,
        category_id: UUID,
        category_data: BudgetCategoryUpdate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> BudgetCategory:
        """Update a budget category (name, description, images)."""
        budget = self.get_budget(budget_id, company_id)

        category = self.budget_category_repository.get_by_id(category_id)
        if not category or category.budget_id != budget_id:
            raise NotFoundException(f"Category with ID {category_id} not found in budget {budget_id}")

        # Create version snapshot before modification
        if budget.status != BudgetStatus.DRAFT:
            self._create_version_snapshot(budget, created_by_user_id, notes="Auto-saved before updating category")

        update_dict = category_data.model_dump(exclude_unset=True)
        self.budget_category_repository.update(category, **update_dict)

        logger.info(f"Updated category {category_id} in budget {budget_id}")
        return category

    def reorder_categories(
        self,
        budget_id: UUID,
        category_ids: List[UUID],
        company_id: UUID,
    ) -> None:
        """Reorder budget categories by setting order_index from the provided list."""
        budget = self.get_budget(budget_id, company_id)
        categories = self.budget_category_repository.get_by_budget(budget_id, include_items=False)

        cat_map = {c.id: c for c in categories}
        for idx, cat_id in enumerate(category_ids):
            cat = cat_map.get(cat_id)
            if cat:
                self.budget_category_repository.update(cat, order_index=idx)

        logger.info(f"Reordered {len(category_ids)} categories in budget {budget_id}")

    def delete_category(
        self,
        budget_id: UUID,
        category_id: UUID,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> bool:
        """Delete a budget category and all its items."""
        budget = self.get_budget(budget_id, company_id)

        category = self.budget_category_repository.get_by_id(category_id)
        if not category or category.budget_id != budget_id:
            raise NotFoundException(f"Category with ID {category_id} not found in budget {budget_id}")

        # Create version snapshot before deletion
        if budget.status != BudgetStatus.DRAFT:
            self._create_version_snapshot(budget, created_by_user_id, notes="Auto-saved before deleting category")

        self.budget_category_repository.delete(category)

        # Recalculate budget total
        budget.total_amount = self.budget_repository.recalculate_total(budget_id)
        self.budget_repository.db.flush()

        logger.info(f"Deleted category {category_id} from budget {budget_id}")
        return True

    # --- Item CRUD ---

    def add_item_to_category(
        self,
        budget_id: UUID,
        category_id: UUID,
        item_data: BudgetItemCreate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> BudgetItem:
        """Add an item to a budget category."""
        budget = self.get_budget(budget_id, company_id)

        category = self.budget_category_repository.get_by_id(category_id)
        if not category or category.budget_id != budget_id:
            raise NotFoundException(f"Category with ID {category_id} not found in budget {budget_id}")

        # Create version snapshot before modification
        if budget.status != BudgetStatus.DRAFT:
            self._create_version_snapshot(budget, created_by_user_id, notes="Auto-saved before adding item")

        # Validate catalog item
        if item_data.catalog_item_id:
            catalog_item = self.catalog_item_repository.get_by_id(item_data.catalog_item_id)
            if not catalog_item:
                raise NotFoundException(f"CatalogItem with ID {item_data.catalog_item_id} not found")
            if catalog_item.company_id != company_id:
                raise ValidationException("CatalogItem does not belong to your company")

        subtotal = item_data.subtotal or (item_data.quantity * item_data.unit_price)

        # Get max order_index
        existing_items = self.budget_item_repository.get_by_category(category_id, include_catalog=False)
        max_order = max([i.order_index for i in existing_items], default=-1) if existing_items else -1

        item = self.budget_item_repository.create(
            description=item_data.description,
            unit=item_data.unit,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            subtotal=subtotal,
            order_index=item_data.order_index if item_data.order_index is not None else (max_order + 1),
            catalog_item_id=item_data.catalog_item_id,
            budget_category_id=category_id
        )

        # Recalculate category subtotal and budget total
        self._recalculate_category_and_budget(category_id, budget)

        logger.info(f"Added item {item.id} to category {category_id}")
        return item

    def update_budget_item(
        self,
        budget_id: UUID,
        category_id: UUID,
        item_id: UUID,
        item_data: BudgetItemUpdate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> BudgetItem:
        """Update a budget item within a category."""
        budget = self.get_budget(budget_id, company_id)

        category = self.budget_category_repository.get_by_id(category_id)
        if not category or category.budget_id != budget_id:
            raise NotFoundException(f"Category with ID {category_id} not found in budget {budget_id}")

        item = self.budget_item_repository.get_by_id(item_id)
        if not item or item.budget_category_id != category_id:
            raise NotFoundException(f"Item with ID {item_id} not found in category {category_id}")

        # Create version snapshot before modification
        if budget.status != BudgetStatus.DRAFT:
            self._create_version_snapshot(budget, created_by_user_id, notes="Auto-saved before updating item")

        # Validate catalog item if being updated
        if item_data.catalog_item_id:
            catalog_item = self.catalog_item_repository.get_by_id(item_data.catalog_item_id)
            if not catalog_item:
                raise NotFoundException(f"CatalogItem with ID {item_data.catalog_item_id} not found")
            if catalog_item.company_id != company_id:
                raise ValidationException("CatalogItem does not belong to your company")

        update_dict = item_data.model_dump(exclude_unset=True)

        # Recalculate subtotal if quantity or unit_price changed
        if "quantity" in update_dict or "unit_price" in update_dict:
            quantity = update_dict.get("quantity", item.quantity)
            unit_price = update_dict.get("unit_price", item.unit_price)
            update_dict["subtotal"] = quantity * unit_price

        self.budget_item_repository.update(item, **update_dict)

        # Recalculate category subtotal and budget total
        self._recalculate_category_and_budget(category_id, budget)

        logger.info(f"Updated item {item_id}")
        return item

    def delete_budget_item(
        self,
        budget_id: UUID,
        category_id: UUID,
        item_id: UUID,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> bool:
        """Delete a budget item from a category."""
        budget = self.get_budget(budget_id, company_id)

        category = self.budget_category_repository.get_by_id(category_id)
        if not category or category.budget_id != budget_id:
            raise NotFoundException(f"Category with ID {category_id} not found in budget {budget_id}")

        item = self.budget_item_repository.get_by_id(item_id)
        if not item or item.budget_category_id != category_id:
            raise NotFoundException(f"Item with ID {item_id} not found in category {category_id}")

        # Create version snapshot before deletion
        if budget.status != BudgetStatus.DRAFT:
            self._create_version_snapshot(budget, created_by_user_id, notes="Auto-saved before deleting item")

        self.budget_item_repository.delete(item)

        # Recalculate category subtotal and budget total
        self._recalculate_category_and_budget(category_id, budget)

        logger.info(f"Deleted item {item_id}")
        return True

    # --- Budget Workflow ---

    def accept_budget(
        self,
        budget_id: UUID,
        company_id: UUID,
        accepted_by_user_id: UUID
    ) -> Tuple[Budget, "Project"]:
        """Accept a budget and update project status to APPROVED."""
        budget = self.get_budget(budget_id, company_id)

        if budget.status != BudgetStatus.PENDING_APPROVAL:
            raise ValidationException(
                f"Cannot accept budget with status {budget.status.value}. "
                "Budget must be in PENDING_APPROVAL status."
            )

        user = self.user_repository.get_by_id(accepted_by_user_id)
        if not user:
            raise NotFoundException(f"User with ID {accepted_by_user_id} not found")
        if user.company_id != company_id:
            raise ValidationException("User does not belong to your company")

        # Create version snapshot before acceptance
        self._create_version_snapshot(budget, accepted_by_user_id, notes="Snapshot before acceptance")

        budget.status = BudgetStatus.ACCEPTED
        budget.accepted_by_user_id = accepted_by_user_id
        budget.accepted_at = datetime.utcnow()

        project = budget.visit.project
        project.status = ProjectStatus.APPROVED

        self.budget_repository.db.flush()
        self.budget_repository.db.refresh(budget)
        self.project_repository.db.refresh(project)

        logger.info(
            f"Budget {budget_id} accepted by user {accepted_by_user_id}. "
            f"Project {project.id} status changed to APPROVED"
        )

        return budget, project

    def reject_budget(self, budget_id: UUID, company_id: UUID) -> Budget:
        """Reject a budget."""
        budget = self.get_budget(budget_id, company_id)

        if budget.status != BudgetStatus.PENDING_APPROVAL:
            raise ValidationException(
                f"Cannot reject budget with status {budget.status.value}. "
                "Budget must be in PENDING_APPROVAL status."
            )

        # Create version snapshot before rejection
        self._create_version_snapshot(budget, notes="Snapshot before rejection")

        budget.status = BudgetStatus.REJECTED
        self.budget_repository.db.flush()
        self.budget_repository.db.refresh(budget)

        logger.info(f"Budget {budget_id} rejected")
        return budget

    def recalculate_budget_total(self, budget_id: UUID, company_id: UUID) -> Budget:
        """Recalculate budget total from all categories and items."""
        budget = self.get_budget(budget_id, company_id)

        # Recalculate each category subtotal
        for category in budget.budget_categories:
            category.subtotal = self.budget_category_repository.recalculate_subtotal(category.id)

        self.budget_repository.db.flush()

        # Recalculate budget total
        budget.total_amount = self.budget_repository.recalculate_total(budget_id)
        self.budget_repository.db.flush()
        self.budget_repository.db.refresh(budget)
        return budget

    # --- Version Management ---

    def create_version(
        self,
        budget_id: UUID,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None,
        notes: Optional[str] = None
    ) -> BudgetVersion:
        """Manually create a version snapshot of the current budget state."""
        budget = self.get_budget(budget_id, company_id)
        return self._create_version_snapshot(budget, created_by_user_id, notes)

    def get_versions(
        self,
        budget_id: UUID,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[BudgetVersion]:
        """Get all versions for a budget."""
        self.get_budget(budget_id, company_id)  # Validate access
        return self.budget_version_repository.get_by_budget(budget_id, skip=skip, limit=limit)

    def get_version(
        self,
        budget_id: UUID,
        version_id: UUID,
        company_id: UUID
    ) -> BudgetVersion:
        """Get a specific version snapshot."""
        self.get_budget(budget_id, company_id)  # Validate access

        version = self.budget_version_repository.get_by_id_with_details(version_id)
        if not version or version.budget_id != budget_id:
            raise NotFoundException(f"Version with ID {version_id} not found for budget {budget_id}")

        return version

    # --- Category Profit CRUD ---

    def _calculate_total_price(
        self,
        provider_price: Decimal,
        delivery_cost: Decimal,
        profit_percentage: Decimal
    ) -> Decimal:
        """Calculate total_price from cost components."""
        return (
            (provider_price + delivery_cost)
            * (1 + profit_percentage / Decimal('100'))
        ).quantize(Decimal('0.01'))

    def set_category_profit(
        self,
        budget_id: UUID,
        category_id: UUID,
        profit_data: CategoryProfitCreate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ):
        """Create or replace profit data for a budget category."""
        from app.models.category_profit import CategoryProfit

        budget = self.get_budget(budget_id, company_id)

        category = self.budget_category_repository.get_by_id(category_id)
        if not category or category.budget_id != budget_id:
            raise NotFoundException(
                f"Category with ID {category_id} not found in budget {budget_id}"
            )

        # Validate creator user
        if created_by_user_id:
            user = self.user_repository.get_by_id(created_by_user_id)
            if not user:
                raise NotFoundException(f"User with ID {created_by_user_id} not found")
            if user.company_id != company_id:
                raise ValidationException("User does not belong to your company")

        total_price = self._calculate_total_price(
            profit_data.provider_price,
            profit_data.delivery_cost,
            profit_data.profit_percentage
        )

        # Version snapshot before modification if not draft
        if budget.status != BudgetStatus.DRAFT:
            self._create_version_snapshot(
                budget, created_by_user_id,
                notes="Auto-saved before updating category profit"
            )

        existing = self.category_profit_repository.get_by_budget_category(category_id)
        if existing:
            # Update existing
            self.category_profit_repository.update(
                existing,
                provider_price=profit_data.provider_price,
                delivery_cost=profit_data.delivery_cost,
                profit_percentage=profit_data.profit_percentage,
                total_price=total_price
            )
            profit = existing
        else:
            # Create new
            profit = self.category_profit_repository.create(
                budget_category_id=category_id,
                provider_price=profit_data.provider_price,
                delivery_cost=profit_data.delivery_cost,
                profit_percentage=profit_data.profit_percentage,
                total_price=total_price,
                created_by_user_id=created_by_user_id
            )

        # Sync total_price → BudgetCategory.subtotal → Budget.total_amount
        category.subtotal = total_price
        self.budget_repository.db.flush()
        budget.total_amount = self.budget_repository.recalculate_total(budget_id)
        self.budget_repository.db.flush()

        logger.info(
            f"Set category profit for category {category_id}: "
            f"total_price={total_price}"
        )
        return profit

    def get_category_profit(
        self,
        budget_id: UUID,
        category_id: UUID,
        company_id: UUID
    ):
        """Get profit data for a specific budget category."""
        self.get_budget(budget_id, company_id)

        category = self.budget_category_repository.get_by_id(category_id)
        if not category or category.budget_id != budget_id:
            raise NotFoundException(
                f"Category with ID {category_id} not found in budget {budget_id}"
            )

        return self.category_profit_repository.get_by_budget_category(category_id)

    def update_category_profit(
        self,
        budget_id: UUID,
        category_id: UUID,
        profit_data: CategoryProfitUpdate,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ):
        """Update specific fields of category profit data."""
        budget = self.get_budget(budget_id, company_id)

        category = self.budget_category_repository.get_by_id(category_id)
        if not category or category.budget_id != budget_id:
            raise NotFoundException(
                f"Category with ID {category_id} not found in budget {budget_id}"
            )

        existing = self.category_profit_repository.get_by_budget_category(category_id)
        if not existing:
            raise NotFoundException(
                f"No profit data found for category {category_id}"
            )

        # Version snapshot before modification if not draft
        if budget.status != BudgetStatus.DRAFT:
            self._create_version_snapshot(
                budget, created_by_user_id,
                notes="Auto-saved before updating category profit"
            )

        update_dict = profit_data.model_dump(exclude_unset=True)
        self.category_profit_repository.update(existing, **update_dict)

        # Recalculate total_price from merged fields
        total_price = self._calculate_total_price(
            existing.provider_price,
            existing.delivery_cost,
            existing.profit_percentage
        )
        existing.total_price = total_price
        self.budget_repository.db.flush()

        # Sync to budget
        category.subtotal = total_price
        self.budget_repository.db.flush()
        budget.total_amount = self.budget_repository.recalculate_total(budget_id)
        self.budget_repository.db.flush()

        logger.info(f"Updated category profit for category {category_id}")
        return existing

    def delete_category_profit(
        self,
        budget_id: UUID,
        category_id: UUID,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None
    ) -> bool:
        """Delete profit data for a budget category."""
        budget = self.get_budget(budget_id, company_id)

        category = self.budget_category_repository.get_by_id(category_id)
        if not category or category.budget_id != budget_id:
            raise NotFoundException(
                f"Category with ID {category_id} not found in budget {budget_id}"
            )

        existing = self.category_profit_repository.get_by_budget_category(category_id)
        if not existing:
            raise NotFoundException(
                f"No profit data found for category {category_id}"
            )

        # Version snapshot before deletion if not draft
        if budget.status != BudgetStatus.DRAFT:
            self._create_version_snapshot(
                budget, created_by_user_id,
                notes="Auto-saved before deleting category profit"
            )

        self.category_profit_repository.delete(existing)

        # Reset category subtotal to sum of items (or 0 if no items)
        category.subtotal = self.budget_category_repository.recalculate_subtotal(category_id)
        self.budget_repository.db.flush()
        budget.total_amount = self.budget_repository.recalculate_total(budget_id)
        self.budget_repository.db.flush()

        logger.info(f"Deleted category profit for category {category_id}")
        return True

    def get_all_profits_for_budget(
        self,
        budget_id: UUID,
        company_id: UUID
    ) -> List:
        """Get all profit data for all categories in a budget."""
        self.get_budget(budget_id, company_id)  # validate access
        return self.category_profit_repository.get_all_by_budget(budget_id)
