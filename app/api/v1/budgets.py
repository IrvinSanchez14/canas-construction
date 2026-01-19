"""
Budget endpoints with dependency injection, clean architecture, and N+1 optimization.

Provides complete CRUD operations for budgets including:
- Creating budgets for visits
- Managing budget items (from catalog or custom)
- Accepting/rejecting budgets (triggers project status update)
- Retrieving budgets with filtering
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_budget_service
from app.services import BudgetService
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetDetailResponse,
    BudgetItemCreate,
    BudgetItemUpdate,
    BudgetItemResponse,
    BudgetItemDetailResponse,
    BudgetAcceptRequest
)
from app.models.budget import BudgetStatus

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post("/", response_model=BudgetDetailResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget: BudgetCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID who is creating this budget (for audit trail)"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Create a new budget for a visit.

    A budget contains line items (products/services) that can be:
    - Selected from catalog (reusable products/services)
    - Custom items (project-specific work)

    Business rules enforced:
    - Visit must exist and belong to the company
    - Visit must not already have a budget (one-to-one relationship)
    - Catalog items (if referenced) must exist and belong to the company
    - Total amount is automatically calculated from items

    **Budget Items:**
    - Can reference catalog items (optional catalog_item_id)
    - Store actual price used (may differ from catalog base price)
    - Support sections (e.g., "PROVISIONALS", "DEMO", "ELECTRICAL")
    - Automatically calculate subtotal (quantity * unit_price)

    **Audit Trail:**
    - Tracks which user created the budget via created_by_user_id
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
    """
    Get all budgets with optional filters.

    **IMPORTANT for CRM:**
    - company_id is REQUIRED for multi-tenant isolation
    - Can filter by visit, status, or both
    - Budget items and catalog references are eagerly loaded (N+1 query optimization)

    **Available Statuses:**
    - draft: Budget being created/edited
    - pending_approval: Budget submitted for client approval
    - accepted: Budget accepted by client
    - rejected: Budget rejected by client
    - revised: Budget revised after rejection
    """
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
    """
    Get a specific budget by ID.

    Includes all budget items with catalog item references for full details.
    """
    budget = service.get_budget(budget_id, company_id)
    return BudgetDetailResponse.from_orm_with_details(budget)


@router.get("/visit/{visit_id}", response_model=BudgetDetailResponse)
def get_budget_by_visit(
    visit_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Get budget for a specific visit.

    Returns the budget associated with the visit, if it exists.
    """
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
    service: BudgetService = Depends(get_budget_service)
):
    """
    Update a budget.

    Can update:
    - Title and description
    - Status (workflow management)
    - Total amount (usually recalculated automatically)

    **Note:** To update budget items, use the item-specific endpoints.
    """
    budget = service.update_budget(budget_id, budget_update, company_id)
    return BudgetDetailResponse.from_orm_with_details(budget)


@router.post("/{budget_id}/items", response_model=BudgetItemDetailResponse, status_code=status.HTTP_201_CREATED)
def add_budget_item(
    budget_id: UUID,
    item: BudgetItemCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Add an item to a budget.

    Items can be:
    - **From catalog**: Provide catalog_item_id, name/unit/price auto-filled (can be customized)
    - **Custom**: Provide description, unit, quantity, unit_price manually

    Budget total is automatically recalculated after adding the item.
    """
    item_obj = service.add_budget_item(budget_id, item, company_id)
    return BudgetItemDetailResponse.from_orm_with_details(item_obj)


@router.put("/{budget_id}/items/{item_id}", response_model=BudgetItemDetailResponse)
def update_budget_item(
    budget_id: UUID,
    item_id: UUID,
    item_update: BudgetItemUpdate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Update a budget item.

    Budget total is automatically recalculated after updating the item.
    """
    item = service.update_budget_item(budget_id, item_id, item_update, company_id)
    return BudgetItemDetailResponse.from_orm_with_details(item)


@router.delete("/{budget_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget_item(
    budget_id: UUID,
    item_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Delete a budget item.

    Budget total is automatically recalculated after deleting the item.
    """
    service.delete_budget_item(budget_id, item_id, company_id)
    return None


@router.post("/{budget_id}/accept", response_model=BudgetDetailResponse)
def accept_budget(
    budget_id: UUID,
    accept_request: BudgetAcceptRequest,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Accept a budget and update project status.

    **Critical Workflow:**
    - Budget status changes to ACCEPTED
    - Project status automatically changes to APPROVED
    - Tracks who accepted and when

    **Business Rules:**
    - Budget must be in PENDING_APPROVAL status
    - User must exist and belong to the company
    - This action triggers the project to move forward

    **Returns:**
    - Updated budget with ACCEPTED status
    - Project status is updated to APPROVED
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
    """
    Reject a budget.

    **Business Rules:**
    - Budget must be in PENDING_APPROVAL status
    - Budget status changes to REJECTED
    - Project status remains unchanged
    """
    budget = service.reject_budget(budget_id, company_id)
    return BudgetDetailResponse.from_orm_with_details(budget)


@router.post("/{budget_id}/recalculate", response_model=BudgetDetailResponse)
def recalculate_budget(
    budget_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: BudgetService = Depends(get_budget_service)
):
    """
    Recalculate budget total from all items.

    Useful if items were modified outside the normal flow or for data integrity checks.
    """
    budget = service.recalculate_budget_total(budget_id, company_id)
    return BudgetDetailResponse.from_orm_with_details(budget)
