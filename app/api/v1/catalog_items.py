"""
Catalog Item endpoints with dependency injection, clean architecture, and audit tracking.
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_catalog_item_service
from app.services import CatalogItemService
from app.schemas.catalog_item import (
    CatalogItemCreate,
    CatalogItemUpdate,
    CatalogItemResponse,
    CatalogItemDetailResponse
)
from app.models.catalog_item import UnitType

router = APIRouter(prefix="/catalog-items", tags=["Catalog Items"])


@router.post("/", response_model=CatalogItemResponse, status_code=status.HTTP_201_CREATED)
def create_catalog_item(
    item: CatalogItemCreate,
    created_by_user_id: Optional[UUID] = Query(None, description="User ID who is creating this item (for audit trail)"),
    service: CatalogItemService = Depends(get_catalog_item_service)
):
    """
    Create a new catalog item.

    Business rules enforced:
    - Company must exist
    - Creator user must belong to the company
    - Price must be positive
    - Name uniqueness is warned but not enforced (allows duplicates)

    **Audit Trail:**
    - Tracks which user created the item via created_by_user_id
    - Useful for accountability and tracking item history
    """
    return service.create_catalog_item(item, created_by_user_id)


@router.get("/", response_model=List[CatalogItemDetailResponse])
def list_catalog_items(
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False, description="Filter only active items"),
    unity: Optional[UnitType] = Query(None, description="Filter by unit type"),
    include_creator: bool = Query(True, description="Include creator details (user who created the item)"),
    service: CatalogItemService = Depends(get_catalog_item_service)
):
    """
    Get all catalog items for a company with optional filters.

    **IMPORTANT for CRM:**
    - company_id is REQUIRED for multi-tenant isolation
    - Creator information is eagerly loaded (N+1 query optimization)
    - Can filter by unit type and active status
    - Uses optimized repository methods

    **Performance:**
    - Without optimization: 1 + N queries (slow)
    - With optimization: 1-2 queries (fast)

    **Available Unit Types:**
    - lb: Pounds
    - sq ft: Square feet
    - ft: Linear feet
    - cu yd: Cubic yards
    - each: Individual items
    - hr: Hours (for labor)
    - day: Days
    """
    items = service.get_catalog_items(
        company_id=company_id,
        skip=skip,
        limit=limit,
        active_only=active_only,
        unity_filter=unity,
        include_creator=include_creator
    )

    # Convert to detail response with creator names
    if include_creator:
        return [CatalogItemDetailResponse.from_orm_with_creator(item) for item in items]
    else:
        return items


@router.get("/by-unity/{unity}", response_model=List[CatalogItemResponse])
def get_items_by_unity(
    unity: UnitType,
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    active_only: bool = Query(True, description="Filter only active items"),
    service: CatalogItemService = Depends(get_catalog_item_service)
):
    """
    Get catalog items filtered by unit type.

    Useful for:
    - Grouping items by measurement unit
    - Building cost estimators
    - Creating material lists
    """
    return service.get_items_by_unity(
        company_id=company_id,
        unity=unity,
        active_only=active_only
    )


@router.get("/{item_id}", response_model=CatalogItemDetailResponse)
def get_catalog_item(
    item_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    include_creator: bool = Query(True, description="Include creator details"),
    service: CatalogItemService = Depends(get_catalog_item_service)
):
    """
    Get a specific catalog item by ID.

    Includes creator information with eager loading (optimized).
    Validates company ownership if company_id provided.
    """
    item = service.get_catalog_item(item_id, company_id, include_creator)

    if include_creator:
        return CatalogItemDetailResponse.from_orm_with_creator(item)
    else:
        return item


@router.put("/{item_id}", response_model=CatalogItemResponse)
def update_catalog_item(
    item_id: UUID,
    item: CatalogItemUpdate,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: CatalogItemService = Depends(get_catalog_item_service)
):
    """
    Update a catalog item.

    Features:
    - Validates company ownership if company_id provided
    - Name uniqueness is warned but not enforced
    - Only updates fields that are provided
    - Cannot change creator (audit trail protection)
    """
    return service.update_catalog_item(item_id, item, company_id)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_item(
    item_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: CatalogItemService = Depends(get_catalog_item_service)
):
    """
    Delete a catalog item (hard delete).

    **WARNING:** This permanently removes the item from the database.

    **RECOMMENDATION:** Use the deactivate endpoint instead to preserve
    historical data for cost breakdowns that reference this item.
    """
    service.delete_catalog_item(item_id, company_id)
    return None


@router.post("/{item_id}/deactivate", response_model=CatalogItemResponse)
def deactivate_catalog_item(
    item_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: CatalogItemService = Depends(get_catalog_item_service)
):
    """
    Deactivate a catalog item (soft delete).

    This is the **RECOMMENDED** approach instead of hard delete because:
    - Preserves historical data
    - Maintains referential integrity
    - Allows reactivation if needed
    - Keeps audit trail intact
    - Cost breakdowns can still reference this item

    The item will:
    - Be hidden from active listings (when active_only=true)
    - Still be accessible by ID for historical reference
    - Can be reactivated using the update endpoint (is_active=true)
    """
    return service.deactivate_catalog_item(item_id, company_id)
