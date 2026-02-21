"""
Rendering Service following SOLID principles.

Business logic for Rendering management:
- Dependency injection
- Multi-tenant isolation
- Validation
- Transaction management
- Image and item management
"""

from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from app.models import Rendering, RenderingStatus
from app.models.rendering import RenderingImage, RenderingItem
from app.models.rendering_version import RenderingVersion
from app.repositories.rendering_repository import (
    RenderingRepository,
    RenderingImageRepository,
    RenderingItemRepository
)
from app.repositories.rendering_version_repository import RenderingVersionRepository
from app.repositories import VisitRepository, BudgetRepository, BudgetItemRepository
from app.schemas.rendering import (
    RenderingCreate,
    RenderingUpdate,
    RenderingImageCreate,
    RenderingImageUpdate,
    RenderingItemCreate,
    RenderingItemUpdate
)
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)


class RenderingService:
    """
    Service layer for Rendering business logic following SOLID principles.

    Dependencies injected:
    - RenderingRepository: Data access for renderings
    - RenderingImageRepository: Data access for images
    - RenderingItemRepository: Data access for items
    - VisitRepository: Visit validation
    - BudgetRepository: Budget validation and item import
    - BudgetItemRepository: Budget item access for importing
    """

    def __init__(
        self,
        rendering_repository: RenderingRepository,
        rendering_image_repository: RenderingImageRepository,
        rendering_item_repository: RenderingItemRepository,
        rendering_version_repository: RenderingVersionRepository,
        visit_repository: VisitRepository,
        budget_repository: BudgetRepository,
        budget_item_repository: BudgetItemRepository
    ):
        """Initialize service with all dependencies injected."""
        self.rendering_repository = rendering_repository
        self.rendering_image_repository = rendering_image_repository
        self.rendering_item_repository = rendering_item_repository
        self.rendering_version_repository = rendering_version_repository
        self.visit_repository = visit_repository
        self.budget_repository = budget_repository
        self.budget_item_repository = budget_item_repository

    # ============== Version Management (internal) ==============

    def _build_snapshot(self, rendering: Rendering) -> dict:
        """Build a JSON snapshot of the current rendering state."""
        images_snapshot = []
        for img in sorted(rendering.images, key=lambda x: x.display_order):
            images_snapshot.append({
                "id": str(img.id),
                "image_url": img.image_url,
                "title": img.title,
                "description": img.description,
                "display_order": img.display_order,
                "is_full_page": img.is_full_page,
                "image_type": img.image_type,
            })

        items_snapshot = []
        for item in sorted(rendering.items, key=lambda x: x.order_index):
            items_snapshot.append({
                "id": str(item.id),
                "category": item.category,
                "name": item.name,
                "specifications": item.specifications,
                "notes": item.notes,
                "image_url": item.image_url,
                "material_image_url": item.material_image_url,
                "product_image_url": item.product_image_url,
                "quantity": str(item.quantity),
                "unit": item.unit,
                "unit_price": str(item.unit_price),
                "subtotal": str(item.subtotal),
                "tax": str(item.tax) if item.tax else None,
                "total": str(item.total),
                "disclaimer": item.disclaimer,
                "is_material_sample": item.is_material_sample,
                "show_in_materials_page": item.show_in_materials_page,
                "show_in_details_page": item.show_in_details_page,
                "order_index": item.order_index,
            })

        return {
            "title": rendering.title,
            "description": rendering.description,
            "notes": rendering.notes,
            "status": rendering.status.value,
            "total_amount": str(rendering.total_amount),
            "expiration_date": str(rendering.expiration_date) if rendering.expiration_date else None,
            "images": images_snapshot,
            "items": items_snapshot,
        }

    def _create_version_snapshot(
        self,
        rendering: Rendering,
        created_by_user_id: Optional[UUID] = None,
        notes: Optional[str] = None
    ) -> RenderingVersion:
        """Create a version snapshot of the current rendering state."""
        next_version = self.rendering_version_repository.get_latest_version_number(rendering.id) + 1
        snapshot = self._build_snapshot(rendering)

        version = self.rendering_version_repository.create(
            rendering_id=rendering.id,
            version_number=next_version,
            snapshot=snapshot,
            notes=notes,
            created_by_user_id=created_by_user_id
        )

        rendering.current_version = next_version
        self.rendering_repository.db.flush()

        logger.info(f"Created version {next_version} for rendering {rendering.id}")
        return version

    # ============== Public Version Methods ==============

    def save_rendering(
        self,
        rendering_id: UUID,
        company_id: UUID,
        created_by_user_id: Optional[UUID] = None,
        notes: Optional[str] = None
    ) -> RenderingVersion:
        """Explicitly save a rendering by creating a version snapshot."""
        rendering = self.get_rendering(rendering_id, company_id)
        return self._create_version_snapshot(rendering, created_by_user_id, notes or "Manual save")

    def get_versions(
        self,
        rendering_id: UUID,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[RenderingVersion]:
        """Get all version snapshots for a rendering."""
        self.get_rendering(rendering_id, company_id)
        return self.rendering_version_repository.get_by_rendering(
            rendering_id=rendering_id,
            skip=skip,
            limit=limit
        )

    def get_version(
        self,
        rendering_id: UUID,
        version_id: UUID,
        company_id: UUID
    ) -> RenderingVersion:
        """Get a specific version snapshot."""
        self.get_rendering(rendering_id, company_id)
        version = self.rendering_version_repository.get_by_id_with_details(version_id)
        if not version or version.rendering_id != rendering_id:
            raise NotFoundException(f"Version with ID {version_id} not found for rendering {rendering_id}")
        return version

    # ============== Rendering CRUD ==============

    def create_rendering(
        self,
        rendering_data: RenderingCreate,
        company_id: UUID
    ) -> Rendering:
        """
        Create a new rendering.

        Business Rules:
        - If visit_id provided, visit must exist and belong to company
        - If budget_id provided, budget must exist and belong to company
        - Multi-tenant isolation enforced

        Args:
            rendering_data: Rendering creation data
            company_id: Company ID for multi-tenant validation

        Returns:
            Created rendering

        Raises:
            NotFoundException: If visit or budget not found
            ValidationException: If visit/budget doesn't belong to company
        """
        # Validate visit if provided
        if rendering_data.visit_id:
            visit = self.visit_repository.get_by_id_with_details(rendering_data.visit_id)
            if not visit:
                raise NotFoundException(f"Visit with ID {rendering_data.visit_id} not found")
            if visit.project.client.company_id != company_id:
                raise ValidationException("Visit does not belong to your company")

        # Validate budget if provided
        if rendering_data.budget_id:
            budget = self.budget_repository.get_by_id_with_details(rendering_data.budget_id)
            if not budget:
                raise NotFoundException(f"Budget with ID {rendering_data.budget_id} not found")
            if budget.visit.project.client.company_id != company_id:
                raise ValidationException("Budget does not belong to your company")

        # Create rendering
        rendering = self.rendering_repository.create(
            title=rendering_data.title,
            description=rendering_data.description,
            notes=rendering_data.notes,
            expiration_date=rendering_data.expiration_date,
            status=rendering_data.status,
            visit_id=rendering_data.visit_id,
            budget_id=rendering_data.budget_id,
            total_amount=Decimal('0')
        )

        logger.info(f"Created rendering {rendering.id}")
        return rendering

    def get_rendering(self, rendering_id: UUID, company_id: UUID) -> Rendering:
        """
        Get a rendering by ID with multi-tenant validation.

        Args:
            rendering_id: Rendering ID
            company_id: Company ID for validation

        Returns:
            Rendering with details

        Raises:
            NotFoundException: If rendering not found
            ValidationException: If rendering doesn't belong to company
        """
        rendering = self.rendering_repository.get_by_id_with_details(rendering_id)
        if not rendering:
            raise NotFoundException(f"Rendering with ID {rendering_id} not found")

        # Validate through visit -> project -> client -> company
        if rendering.visit and rendering.visit.project.client.company_id != company_id:
            raise ValidationException("Rendering does not belong to your company")

        return rendering

    def get_renderings(
        self,
        company_id: UUID,
        visit_id: Optional[UUID] = None,
        budget_id: Optional[UUID] = None,
        status: Optional[RenderingStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Rendering]:
        """
        Get renderings with optional filters and multi-tenant isolation.

        Args:
            company_id: Company ID for multi-tenant validation
            visit_id: Optional visit filter
            budget_id: Optional budget filter
            status: Optional status filter
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of renderings
        """
        if visit_id:
            visit = self.visit_repository.get_by_id_with_details(visit_id)
            if not visit:
                raise NotFoundException(f"Visit with ID {visit_id} not found")
            if visit.project.client.company_id != company_id:
                raise ValidationException("Visit does not belong to your company")
            return self.rendering_repository.get_by_visit(
                visit_id=visit_id,
                skip=skip,
                limit=limit,
                status=status
            )

        if budget_id:
            budget = self.budget_repository.get_by_id_with_details(budget_id)
            if not budget:
                raise NotFoundException(f"Budget with ID {budget_id} not found")
            if budget.visit.project.client.company_id != company_id:
                raise ValidationException("Budget does not belong to your company")
            return self.rendering_repository.get_by_budget(
                budget_id=budget_id,
                skip=skip,
                limit=limit
            )

        return self.rendering_repository.get_all_by_company(
            company_id=company_id,
            skip=skip,
            limit=limit,
            status=status
        )

    def update_rendering(
        self,
        rendering_id: UUID,
        rendering_data: RenderingUpdate,
        company_id: UUID
    ) -> Rendering:
        """
        Update a rendering.

        Args:
            rendering_id: Rendering ID
            rendering_data: Update data
            company_id: Company ID for validation

        Returns:
            Updated rendering
        """
        rendering = self.get_rendering(rendering_id, company_id)

        # Create version snapshot before modification
        if rendering.status != RenderingStatus.DRAFT:
            self._create_version_snapshot(rendering, notes="Auto-saved before update")

        # Validate new visit if provided
        if rendering_data.visit_id and rendering_data.visit_id != rendering.visit_id:
            visit = self.visit_repository.get_by_id_with_details(rendering_data.visit_id)
            if not visit:
                raise NotFoundException(f"Visit with ID {rendering_data.visit_id} not found")
            if visit.project.client.company_id != company_id:
                raise ValidationException("Visit does not belong to your company")

        # Validate new budget if provided
        if rendering_data.budget_id and rendering_data.budget_id != rendering.budget_id:
            budget = self.budget_repository.get_by_id_with_details(rendering_data.budget_id)
            if not budget:
                raise NotFoundException(f"Budget with ID {rendering_data.budget_id} not found")
            if budget.visit.project.client.company_id != company_id:
                raise ValidationException("Budget does not belong to your company")

        # Update fields
        update_dict = rendering_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(rendering, key, value)

        self.rendering_repository.db.flush()
        self.rendering_repository.db.refresh(rendering)

        logger.info(f"Updated rendering {rendering_id}")
        return rendering

    def delete_rendering(self, rendering_id: UUID, company_id: UUID) -> bool:
        """
        Delete a rendering with multi-tenant validation.

        Args:
            rendering_id: Rendering ID
            company_id: Company ID for validation

        Returns:
            True if deleted
        """
        rendering = self.get_rendering(rendering_id, company_id)
        self.rendering_repository.delete(rendering)
        logger.info(f"Deleted rendering {rendering_id}")
        return True

    def change_status(
        self,
        rendering_id: UUID,
        new_status: RenderingStatus,
        company_id: UUID,
        sent_to_email: Optional[str] = None,
        approved_by_client_name: Optional[str] = None
    ) -> Rendering:
        """
        Change rendering status (workflow management).

        Args:
            rendering_id: Rendering ID
            new_status: New status
            company_id: Company ID for validation
            sent_to_email: Email address if status is SENT
            approved_by_client_name: Client name if status is APPROVED

        Returns:
            Updated rendering
        """
        rendering = self.get_rendering(rendering_id, company_id)

        # Create version snapshot before status change
        self._create_version_snapshot(rendering, notes=f"Snapshot before status change to {new_status.value}")

        rendering.status = new_status

        if new_status == RenderingStatus.SENT:
            rendering.sent_at = datetime.utcnow()
            if sent_to_email:
                rendering.sent_to_email = sent_to_email

        if new_status == RenderingStatus.APPROVED:
            rendering.approved_at = datetime.utcnow()
            if approved_by_client_name:
                rendering.approved_by_client_name = approved_by_client_name

        self.rendering_repository.db.flush()
        self.rendering_repository.db.refresh(rendering)

        logger.info(f"Changed rendering {rendering_id} status to {new_status}")
        return rendering

    # ============== Image Management ==============

    def add_image(
        self,
        rendering_id: UUID,
        image_data: RenderingImageCreate,
        company_id: UUID
    ) -> RenderingImage:
        """Add an image to a rendering."""
        rendering = self.get_rendering(rendering_id, company_id)

        # Create version snapshot before modification
        if rendering.status != RenderingStatus.DRAFT:
            self._create_version_snapshot(rendering, notes="Auto-saved before adding image")

        # Auto-set display order if not provided
        if image_data.display_order == 0:
            max_order = self.rendering_image_repository.get_max_display_order(rendering_id)
            image_data.display_order = max_order + 1

        image = self.rendering_image_repository.create(
            rendering_id=rendering_id,
            **image_data.model_dump()
        )

        logger.info(f"Added image {image.id} to rendering {rendering_id}")
        return image

    def update_image(
        self,
        rendering_id: UUID,
        image_id: UUID,
        image_data: RenderingImageUpdate,
        company_id: UUID
    ) -> RenderingImage:
        """Update an image in a rendering."""
        self.get_rendering(rendering_id, company_id)

        image = self.rendering_image_repository.get_by_id(image_id)
        if not image or image.rendering_id != rendering_id:
            raise NotFoundException(f"Image with ID {image_id} not found in rendering")

        update_dict = image_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(image, key, value)

        self.rendering_image_repository.db.flush()
        self.rendering_image_repository.db.refresh(image)

        logger.info(f"Updated image {image_id}")
        return image

    def delete_image(
        self,
        rendering_id: UUID,
        image_id: UUID,
        company_id: UUID
    ) -> bool:
        """Delete an image from a rendering."""
        rendering = self.get_rendering(rendering_id, company_id)

        # Create version snapshot before modification
        if rendering.status != RenderingStatus.DRAFT:
            self._create_version_snapshot(rendering, notes="Auto-saved before deleting image")

        image = self.rendering_image_repository.get_by_id(image_id)
        if not image or image.rendering_id != rendering_id:
            raise NotFoundException(f"Image with ID {image_id} not found in rendering")

        self.rendering_image_repository.delete(image)
        logger.info(f"Deleted image {image_id}")
        return True

    def reorder_images(
        self,
        rendering_id: UUID,
        image_ids: List[UUID],
        company_id: UUID
    ) -> List[RenderingImage]:
        """
        Reorder images in a rendering.

        Args:
            rendering_id: Rendering ID
            image_ids: Ordered list of image IDs
            company_id: Company ID for validation

        Returns:
            Updated list of images
        """
        self.get_rendering(rendering_id, company_id)

        # Validate all images belong to this rendering
        existing_images = self.rendering_image_repository.get_by_rendering(rendering_id)
        existing_ids = {img.id for img in existing_images}

        for img_id in image_ids:
            if img_id not in existing_ids:
                raise ValidationException(f"Image {img_id} does not belong to this rendering")

        # Update orders
        image_orders = [(img_id, idx) for idx, img_id in enumerate(image_ids)]
        self.rendering_image_repository.bulk_update_order(image_orders)

        return self.rendering_image_repository.get_by_rendering(rendering_id)

    # ============== Item Management ==============

    def add_item(
        self,
        rendering_id: UUID,
        item_data: RenderingItemCreate,
        company_id: UUID
    ) -> RenderingItem:
        """Add an item to a rendering."""
        rendering = self.get_rendering(rendering_id, company_id)

        # Create version snapshot before modification
        if rendering.status != RenderingStatus.DRAFT:
            self._create_version_snapshot(rendering, notes="Auto-saved before adding item")

        # Auto-set order index if not provided
        if item_data.order_index == 0:
            max_order = self.rendering_item_repository.get_max_order_index(rendering_id)
            item_data.order_index = max_order + 1

        # Calculate subtotal and total (including tax if provided)
        subtotal = item_data.quantity * item_data.unit_price
        tax_amount = item_data.tax if item_data.tax else Decimal('0')
        total = subtotal + tax_amount

        item = self.rendering_item_repository.create(
            rendering_id=rendering_id,
            subtotal=subtotal,
            total=total,
            **item_data.model_dump(exclude={'subtotal', 'total'})
        )

        # Update rendering total
        self._update_rendering_total(rendering_id)

        logger.info(f"Added item {item.id} to rendering {rendering_id}")
        return item

    def update_item(
        self,
        rendering_id: UUID,
        item_id: UUID,
        item_data: RenderingItemUpdate,
        company_id: UUID
    ) -> RenderingItem:
        """Update an item in a rendering."""
        rendering = self.get_rendering(rendering_id, company_id)

        # Create version snapshot before modification
        if rendering.status != RenderingStatus.DRAFT:
            self._create_version_snapshot(rendering, notes="Auto-saved before updating item")

        item = self.rendering_item_repository.get_by_id(item_id)
        if not item or item.rendering_id != rendering_id:
            raise NotFoundException(f"Item with ID {item_id} not found in rendering")

        update_dict = item_data.model_dump(exclude_unset=True)

        # Recalculate subtotal and total if price fields changed
        quantity = update_dict.get('quantity', item.quantity)
        unit_price = update_dict.get('unit_price', item.unit_price)
        tax = update_dict.get('tax', item.tax) or Decimal('0')
        update_dict['subtotal'] = quantity * unit_price
        update_dict['total'] = update_dict['subtotal'] + tax

        for key, value in update_dict.items():
            setattr(item, key, value)

        self.rendering_item_repository.db.flush()
        self.rendering_item_repository.db.refresh(item)

        # Update rendering total
        self._update_rendering_total(rendering_id)

        logger.info(f"Updated item {item_id}")
        return item

    def delete_item(
        self,
        rendering_id: UUID,
        item_id: UUID,
        company_id: UUID
    ) -> bool:
        """Delete an item from a rendering."""
        rendering = self.get_rendering(rendering_id, company_id)

        # Create version snapshot before modification
        if rendering.status != RenderingStatus.DRAFT:
            self._create_version_snapshot(rendering, notes="Auto-saved before deleting item")

        item = self.rendering_item_repository.get_by_id(item_id)
        if not item or item.rendering_id != rendering_id:
            raise NotFoundException(f"Item with ID {item_id} not found in rendering")

        self.rendering_item_repository.delete(item)

        # Update rendering total
        self._update_rendering_total(rendering_id)

        logger.info(f"Deleted item {item_id}")
        return True

    def import_budget_items(
        self,
        rendering_id: UUID,
        budget_id: UUID,
        company_id: UUID,
        item_ids: Optional[List[UUID]] = None
    ) -> List[RenderingItem]:
        """
        Import items from a budget into the rendering.

        Args:
            rendering_id: Rendering ID
            budget_id: Budget ID to import from
            company_id: Company ID for validation
            item_ids: Specific item IDs to import (None = all items)

        Returns:
            List of created rendering items
        """
        rendering = self.get_rendering(rendering_id, company_id)

        # Validate budget
        budget = self.budget_repository.get_by_id_with_details(budget_id)
        if not budget:
            raise NotFoundException(f"Budget with ID {budget_id} not found")
        if budget.visit.project.client.company_id != company_id:
            raise ValidationException("Budget does not belong to your company")

        # Get budget items from all categories
        budget_items = []
        for cat in budget.budget_categories:
            for bi in cat.budget_items:
                budget_items.append((cat.name, bi))

        if item_ids:
            budget_items = [(cat_name, bi) for cat_name, bi in budget_items if bi.id in item_ids]

        # Get current max order
        max_order = self.rendering_item_repository.get_max_order_index(rendering_id)

        created_items = []
        for idx, (cat_name, bi) in enumerate(budget_items):
            item = self.rendering_item_repository.create(
                rendering_id=rendering_id,
                category=cat_name,
                name=bi.description,
                specifications=None,
                notes=None,
                image_url=None,
                quantity=bi.quantity,
                unit=bi.unit,
                unit_price=bi.unit_price,
                subtotal=bi.subtotal,
                total=bi.subtotal,
                order_index=max_order + idx + 1,
                budget_item_id=bi.id
            )
            created_items.append(item)

        # Update rendering total and link to budget
        rendering.budget_id = budget_id
        self._update_rendering_total(rendering_id)

        logger.info(f"Imported {len(created_items)} items from budget {budget_id} to rendering {rendering_id}")
        return created_items

    def _update_rendering_total(self, rendering_id: UUID) -> None:
        """Update the total amount for a rendering based on its items."""
        total = self.rendering_item_repository.calculate_total(rendering_id)
        rendering = self.rendering_repository.get_by_id(rendering_id)
        if rendering:
            rendering.total_amount = Decimal(str(total))
            self.rendering_repository.db.flush()
