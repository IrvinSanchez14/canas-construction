"""
Catalog Item Service following SOLID principles.

Business logic for CatalogItem management:
- Dependency injection
- Multi-tenant isolation
- User tracking for audit trail
- Validation
- Transaction management
"""

from typing import List, Optional
from uuid import UUID

from app.models import CatalogItem, UnitType
from app.repositories import CatalogItemRepository, CompanyRepository, UserRepository
from app.schemas.catalog_item import CatalogItemCreate, CatalogItemUpdate
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    ValidationException
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class CatalogItemService:
    """
    Service layer for CatalogItem business logic following SOLID principles.

    Dependencies injected:
    - CatalogItemRepository: Data access
    - CompanyRepository: Company validation
    - UserRepository: User validation for creator tracking
    """

    def __init__(
        self,
        catalog_item_repository: CatalogItemRepository,
        company_repository: CompanyRepository,
        user_repository: UserRepository
    ):
        """Initialize service with all dependencies injected."""
        self.catalog_item_repository = catalog_item_repository
        self.company_repository = company_repository
        self.user_repository = user_repository

    def create_catalog_item(
        self,
        item_data: CatalogItemCreate,
        created_by_user_id: Optional[UUID] = None
    ) -> CatalogItem:
        """
        Create a new catalog item.

        Business Rules:
        - Company must exist
        - Item name should be unique within company (warning, not strict)
        - Creator user must exist and belong to the company
        - Price must be positive

        Args:
            item_data: Catalog item creation data
            created_by_user_id: User ID who is creating this item (for audit)

        Returns:
            Created catalog item

        Raises:
            NotFoundException: If company or user not found
            ValidationException: If user doesn't belong to company
        """
        logger.info(f"Creating catalog item: {item_data.name} for company {item_data.company_id}")

        # Validate company exists
        self.company_repository.get_by_id_or_fail(item_data.company_id)

        # Use provided creator or fallback to item_data
        creator_id = created_by_user_id or item_data.created_by_user_id

        # Validate creator user if provided
        if creator_id:
            user = self.user_repository.get_by_id(creator_id)
            if not user:
                raise NotFoundException("User", creator_id)

            # Validate user belongs to the company
            if user.company_id != item_data.company_id:
                raise ValidationException(
                    f"User {creator_id} does not belong to company {item_data.company_id}"
                )

        # Check if name already exists (warning, not error)
        if self.catalog_item_repository.exists_by_name(item_data.name, item_data.company_id):
            logger.warning(
                f"Catalog item with name '{item_data.name}' already exists for company {item_data.company_id}"
            )

        # Create catalog item
        catalog_item = self.catalog_item_repository.create(
            name=item_data.name,
            description=item_data.description,
            unity=item_data.unity,
            price_base=item_data.price_base,
            is_active=item_data.is_active,
            company_id=item_data.company_id,
            created_by_user_id=creator_id
        )

        logger.info(f"Catalog item created successfully: {catalog_item.id}")
        return catalog_item

    def get_catalog_item(
        self,
        item_id: UUID,
        company_id: Optional[UUID] = None,
        include_creator: bool = False
    ) -> CatalogItem:
        """
        Get catalog item by ID with optional company filter.

        Args:
            item_id: Catalog item ID
            company_id: Optional company filter for multi-tenant isolation
            include_creator: Whether to include creator details

        Returns:
            Catalog item with optional creator info

        Raises:
            NotFoundException: If item not found
            ValidationException: If item doesn't belong to company
        """
        if include_creator:
            item = self.catalog_item_repository.get_by_id_with_creator(item_id)
        else:
            item = self.catalog_item_repository.get_by_id(item_id)

        if not item:
            raise NotFoundException("CatalogItem", item_id)

        # Validate company ownership if company_id provided
        if company_id is not None and item.company_id != company_id:
            raise ValidationException(
                f"CatalogItem {item_id} does not belong to company {company_id}"
            )

        return item

    def get_catalog_items(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
        unity_filter: Optional[UnitType] = None,
        include_creator: bool = False
    ) -> List[CatalogItem]:
        """
        Get catalog items for a company with optional filters.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit
            active_only: Filter only active items
            unity_filter: Filter by unit type
            include_creator: Whether to include creator details (N+1 optimized)

        Returns:
            List of catalog items
        """
        return self.catalog_item_repository.get_by_company(
            company_id=company_id,
            skip=skip,
            limit=limit,
            active_only=active_only,
            unity_filter=unity_filter,
            include_creator=include_creator
        )

    def update_catalog_item(
        self,
        item_id: UUID,
        item_data: CatalogItemUpdate,
        company_id: Optional[UUID] = None
    ) -> CatalogItem:
        """
        Update catalog item.

        Business Rules:
        - Item name should remain unique within company (if changed)
        - Cannot change creator (audit trail protection)

        Args:
            item_id: Catalog item ID
            item_data: Update data
            company_id: Optional company filter

        Returns:
            Updated catalog item

        Raises:
            NotFoundException: If item not found
        """
        logger.info(f"Updating catalog item: {item_id}")

        # Get item
        item = self.get_catalog_item(item_id, company_id)

        update_data = item_data.model_dump(exclude_unset=True)

        # Check name uniqueness if changing name
        if "name" in update_data and update_data["name"] != item.name:
            if self.catalog_item_repository.exists_by_name(
                update_data["name"],
                item.company_id,
                exclude_id=item_id
            ):
                logger.warning(
                    f"Catalog item with name '{update_data['name']}' already exists for company {item.company_id}"
                )

        # Update item
        updated_item = self.catalog_item_repository.update(item, **update_data)
        logger.info(f"Catalog item updated successfully: {item_id}")

        return updated_item

    def delete_catalog_item(
        self,
        item_id: UUID,
        company_id: Optional[UUID] = None
    ) -> None:
        """
        Delete catalog item.

        Args:
            item_id: Catalog item ID
            company_id: Optional company filter

        Raises:
            NotFoundException: If item not found
        """
        logger.warning(f"Deleting catalog item: {item_id}")

        item = self.get_catalog_item(item_id, company_id)
        self.catalog_item_repository.delete(item)

        logger.info(f"Catalog item deleted successfully: {item_id}")

    def deactivate_catalog_item(
        self,
        item_id: UUID,
        company_id: Optional[UUID] = None
    ) -> CatalogItem:
        """
        Deactivate catalog item instead of deleting (soft delete).

        This is the recommended approach to preserve historical data
        for cost breakdowns that may reference this item.

        Args:
            item_id: Catalog item ID
            company_id: Optional company filter

        Returns:
            Deactivated catalog item
        """
        logger.info(f"Deactivating catalog item: {item_id}")

        item = self.get_catalog_item(item_id, company_id)
        updated_item = self.catalog_item_repository.update(item, is_active=False)

        logger.info(f"Catalog item deactivated successfully: {item_id}")
        return updated_item

    def get_items_by_unity(
        self,
        company_id: UUID,
        unity: UnitType,
        active_only: bool = True
    ) -> List[CatalogItem]:
        """
        Get catalog items filtered by unit type.

        Useful for displaying items grouped by measurement unit.

        Args:
            company_id: Company ID
            unity: Unit type to filter by
            active_only: Only return active items

        Returns:
            List of catalog items with specified unit type
        """
        return self.catalog_item_repository.get_by_unity(
            company_id=company_id,
            unity=unity,
            active_only=active_only
        )

    def count_catalog_items(
        self,
        company_id: UUID,
        active_only: bool = False
    ) -> int:
        """Count catalog items for a company."""
        return self.catalog_item_repository.count_by_company(
            company_id=company_id,
            active_only=active_only
        )
