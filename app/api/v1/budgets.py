"""
Budget endpoints with categories, items, and versioning.

Structure: Budget → Categories → Items
Provides complete CRUD for budgets, categories, items, and version history.
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_budget_service
from app.services import BudgetService
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetDetailResponse,
    BudgetCategoryCreate,
    BudgetCategoryDetailResponse,
    BudgetItemCreate,
    BudgetItemUpdate,
    BudgetItemDetailResponse,
    BudgetAcceptRequest
)
from app.schemas.budget_category import BudgetCategoryUpdate
from app.schemas.budget_version import BudgetVersionResponse, BudgetVersionListResponse
from app.schemas.category_profit import (
    CategoryProfitCreate,
    CategoryProfitUpdate,
    CategoryProfitResponse,
)
from app.models.budget import BudgetStatus

router = APIRouter(prefix="/budgets", tags=["Budgets"])


# --- Budget CRUD ---

@router.post("/", response_model=BudgetDetailResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget: BudgetCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID who is creating this budget"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Create a new budget for a visit with categories and items.

    Structure: Budget → Categories → Items
    Each category can contain multiple items and up to 3 images.
    """
    budget_obj = service.create_budget(budget, company_id, created_by_user_id)
    return BudgetDetailResponse.from_orm_with_details(budget_obj)


@router.get("/", response_model=List[BudgetDetailResponse])
def list_budgets(
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    visit_id: Optional[UUID] = Query(None, description="Filter by visit ID"),
    status_filter: Optional[BudgetStatus] = Query(None, alias="status", description="Filter by budget status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: BudgetService = Depends(get_budget_service)
):
    """Get all budgets with optional filters."""
    budgets = service.get_budgets(
        company_id=company_id,
        visit_id=visit_id,
        status=status_filter,
        skip=skip,
        limit=limit
    )
    return [BudgetDetailResponse.from_orm_with_details(budget) for budget in budgets]


@router.get("/{budget_id}", response_model=BudgetDetailResponse)
def get_budget(
    budget_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """Get a specific budget by ID with all categories and items."""
    budget = service.get_budget(budget_id, company_id)
    return BudgetDetailResponse.from_orm_with_details(budget)


@router.get("/visit/{visit_id}", response_model=BudgetDetailResponse)
def get_budget_by_visit(
    visit_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """Get budget for a specific visit."""
    budget = service.get_budget_by_visit(visit_id, company_id)
    if not budget:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No budget found for visit {visit_id}"
        )
    return BudgetDetailResponse.from_orm_with_details(budget)


@router.put("/{budget_id}", response_model=BudgetDetailResponse)
def update_budget(
    budget_id: UUID,
    budget_update: BudgetUpdate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID making the update"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Update a budget (title, description, status).

    A version snapshot is automatically saved before modifying non-draft budgets.
    """
    budget = service.update_budget(budget_id, budget_update, company_id, created_by_user_id)
    return BudgetDetailResponse.from_orm_with_details(budget)


# --- Category CRUD ---

@router.post("/{budget_id}/categories", response_model=BudgetCategoryDetailResponse, status_code=status.HTTP_201_CREATED)
def add_category(
    budget_id: UUID,
    category: BudgetCategoryCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID making the change"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Add a category to a budget with optional items.

    Each category can have up to 3 images and multiple items.
    """
    cat_obj = service.add_category(budget_id, category, company_id, created_by_user_id)
    return BudgetCategoryDetailResponse.from_orm_with_details(cat_obj)


@router.put("/{budget_id}/categories/{category_id}", response_model=BudgetCategoryDetailResponse)
def update_category(
    budget_id: UUID,
    category_id: UUID,
    category_update: BudgetCategoryUpdate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID making the change"),
    service: BudgetService = Depends(get_budget_service)
):
    """Update a budget category (name, description, images)."""
    cat_obj = service.update_category(budget_id, category_id, category_update, company_id, created_by_user_id)
    return BudgetCategoryDetailResponse.from_orm_with_details(cat_obj)


@router.delete("/{budget_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    budget_id: UUID,
    category_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID making the change"),
    service: BudgetService = Depends(get_budget_service)
):
    """Delete a budget category and all its items."""
    service.delete_category(budget_id, category_id, company_id, created_by_user_id)
    return None


# --- Item CRUD (within categories) ---

@router.post(
    "/{budget_id}/categories/{category_id}/items",
    response_model=BudgetItemDetailResponse,
    status_code=status.HTTP_201_CREATED
)
def add_item_to_category(
    budget_id: UUID,
    category_id: UUID,
    item: BudgetItemCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID making the change"),
    service: BudgetService = Depends(get_budget_service)
):
    """Add an item to a budget category. Subtotal is auto-calculated."""
    item_obj = service.add_item_to_category(budget_id, category_id, item, company_id, created_by_user_id)
    return BudgetItemDetailResponse.from_orm_with_details(item_obj)


@router.put(
    "/{budget_id}/categories/{category_id}/items/{item_id}",
    response_model=BudgetItemDetailResponse
)
def update_item(
    budget_id: UUID,
    category_id: UUID,
    item_id: UUID,
    item_update: BudgetItemUpdate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID making the change"),
    service: BudgetService = Depends(get_budget_service)
):
    """Update a budget item. Subtotal is recalculated if quantity or unit_price changes."""
    item_obj = service.update_budget_item(budget_id, category_id, item_id, item_update, company_id, created_by_user_id)
    return BudgetItemDetailResponse.from_orm_with_details(item_obj)


@router.delete(
    "/{budget_id}/categories/{category_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_item(
    budget_id: UUID,
    category_id: UUID,
    item_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID making the change"),
    service: BudgetService = Depends(get_budget_service)
):
    """Delete a budget item from a category."""
    service.delete_budget_item(budget_id, category_id, item_id, company_id, created_by_user_id)
    return None


# --- Category Profit (internal cost breakdown) ---

@router.put(
    "/{budget_id}/categories/{category_id}/profit",
    response_model=CategoryProfitResponse,
    status_code=status.HTTP_200_OK
)
def set_category_profit(
    budget_id: UUID,
    category_id: UUID,
    profit_data: CategoryProfitCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID making the change"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Set profit breakdown for a budget category (create or replace).

    Calculates total_price as: (provider_price + delivery_cost) * (1 + profit_percentage/100).
    Updates the category subtotal and budget total automatically.
    """
    profit = service.set_category_profit(
        budget_id, category_id, profit_data, company_id, created_by_user_id
    )
    return CategoryProfitResponse.from_orm_with_details(profit)


@router.get(
    "/{budget_id}/categories/{category_id}/profit",
    response_model=CategoryProfitResponse
)
def get_category_profit(
    budget_id: UUID,
    category_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """Get profit breakdown for a budget category."""
    profit = service.get_category_profit(budget_id, category_id, company_id)
    if not profit:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No profit data found for category {category_id}"
        )
    return CategoryProfitResponse.from_orm_with_details(profit)


@router.patch(
    "/{budget_id}/categories/{category_id}/profit",
    response_model=CategoryProfitResponse
)
def update_category_profit(
    budget_id: UUID,
    category_id: UUID,
    profit_data: CategoryProfitUpdate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID making the change"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Partially update profit data for a budget category.

    Recalculates total_price and updates budget totals automatically.
    """
    profit = service.update_category_profit(
        budget_id, category_id, profit_data, company_id, created_by_user_id
    )
    return CategoryProfitResponse.from_orm_with_details(profit)


@router.delete(
    "/{budget_id}/categories/{category_id}/profit",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_category_profit(
    budget_id: UUID,
    category_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID making the change"),
    service: BudgetService = Depends(get_budget_service)
):
    """Delete profit data for a budget category. Resets subtotal to sum of items."""
    service.delete_category_profit(budget_id, category_id, company_id, created_by_user_id)
    return None


@router.get(
    "/{budget_id}/profits",
    response_model=List[CategoryProfitResponse]
)
def list_budget_profits(
    budget_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """Get all profit data for all categories in a budget."""
    profits = service.get_all_profits_for_budget(budget_id, company_id)
    return [CategoryProfitResponse.from_orm_with_details(p) for p in profits]


# --- Budget Workflow ---

@router.post("/{budget_id}/accept", response_model=BudgetDetailResponse)
def accept_budget(
    budget_id: UUID,
    accept_request: BudgetAcceptRequest,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Accept a budget and update project status to APPROVED.

    A version snapshot is saved before acceptance.
    Budget must be in PENDING_APPROVAL status.
    """
    budget, project = service.accept_budget(
        budget_id,
        company_id,
        accept_request.accepted_by_user_id
    )
    return BudgetDetailResponse.from_orm_with_details(budget)


@router.post("/{budget_id}/reject", response_model=BudgetDetailResponse)
def reject_budget(
    budget_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """Reject a budget. Must be in PENDING_APPROVAL status."""
    budget = service.reject_budget(budget_id, company_id)
    return BudgetDetailResponse.from_orm_with_details(budget)


@router.post("/{budget_id}/recalculate", response_model=BudgetDetailResponse)
def recalculate_budget(
    budget_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """Recalculate budget total from all categories and items."""
    budget = service.recalculate_budget_total(budget_id, company_id)
    return BudgetDetailResponse.from_orm_with_details(budget)


# --- Version History ---

@router.get("/{budget_id}/versions", response_model=BudgetVersionListResponse)
def list_versions(
    budget_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: BudgetService = Depends(get_budget_service)
):
    """Get all version snapshots for a budget (most recent first)."""
    versions = service.get_versions(budget_id, company_id, skip=skip, limit=limit)
    return BudgetVersionListResponse(
        versions=[BudgetVersionResponse.from_orm_with_details(v) for v in versions],
        total=len(versions),
        skip=skip,
        limit=limit
    )


@router.get("/{budget_id}/versions/{version_id}", response_model=BudgetVersionResponse)
def get_version(
    budget_id: UUID,
    version_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """Get a specific version snapshot with full budget data."""
    version = service.get_version(budget_id, version_id, company_id)
    return BudgetVersionResponse.from_orm_with_details(version)
