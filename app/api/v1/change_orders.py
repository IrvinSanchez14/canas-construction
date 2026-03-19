"""
Change Order API endpoints.

Provides CRUD operations for change orders, item management,
workflow (accept/reject/apply), and PDF generation.
"""

from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import StreamingResponse

from app.schemas.change_order import (
    ChangeOrderCreate,
    ChangeOrderUpdate,
    ChangeOrderDetailResponse,
    ChangeOrderListResponse,
    ChangeOrderItemCreate,
    ChangeOrderItemUpdate,
    ChangeOrderItemResponse,
)
from app.services.change_order_service import ChangeOrderService
from app.services.change_order_pdf_service import ChangeOrderPDFService, get_change_order_pdf_service
from app.core.dependencies import get_change_order_service

router = APIRouter(prefix="/change-orders", tags=["Change Orders"])


# --- Change Order CRUD ---

@router.post(
    "/",
    response_model=ChangeOrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new change order"
)
def create_change_order(
    change_order_data: ChangeOrderCreate,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    created_by_user_id: UUID = Query(None, description="User ID of the creator"),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """Create a new change order with items for a budget."""
    change_order = service.create_change_order(
        data=change_order_data,
        company_id=company_id,
        created_by_user_id=created_by_user_id
    )
    return ChangeOrderDetailResponse.from_orm_with_details(change_order)


@router.get(
    "/",
    response_model=ChangeOrderListResponse,
    summary="List change orders"
)
def list_change_orders(
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    project_id: UUID = Query(None, description="Filter by project ID"),
    status_filter: str = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """List change orders with optional filters."""
    change_orders, total = service.get_change_orders(
        company_id=company_id,
        project_id=project_id,
        status=status_filter,
        skip=skip,
        limit=limit
    )
    return ChangeOrderListResponse(
        change_orders=[
            ChangeOrderDetailResponse.from_orm_with_details(co)
            for co in change_orders
        ],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get(
    "/{change_order_id}",
    response_model=ChangeOrderDetailResponse,
    summary="Get change order details"
)
def get_change_order(
    change_order_id: UUID,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """Get a specific change order with all details."""
    change_order = service.get_change_order(change_order_id, company_id)
    return ChangeOrderDetailResponse.from_orm_with_details(change_order)


@router.put(
    "/{change_order_id}",
    response_model=ChangeOrderDetailResponse,
    summary="Update a change order"
)
def update_change_order(
    change_order_id: UUID,
    change_order_data: ChangeOrderUpdate,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """Update a change order's title, description, or observations."""
    change_order = service.update_change_order(change_order_id, change_order_data, company_id)
    return ChangeOrderDetailResponse.from_orm_with_details(change_order)


@router.delete(
    "/{change_order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a change order"
)
def delete_change_order(
    change_order_id: UUID,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """Delete a change order (cannot delete applied ones)."""
    service.delete_change_order(change_order_id, company_id)


# --- Item Management ---

@router.post(
    "/{change_order_id}/items",
    response_model=ChangeOrderItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to change order"
)
def add_item(
    change_order_id: UUID,
    item_data: ChangeOrderItemCreate,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """Add a new item to a change order."""
    item = service.add_item(change_order_id, item_data, company_id)
    return ChangeOrderItemResponse(**{
        k: v for k, v in item.__dict__.items() if not k.startswith('_')
    })


@router.put(
    "/{change_order_id}/items/{item_id}",
    response_model=ChangeOrderItemResponse,
    summary="Update change order item"
)
def update_item(
    change_order_id: UUID,
    item_id: UUID,
    item_data: ChangeOrderItemUpdate,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """Update an existing item in a change order."""
    item = service.update_item(change_order_id, item_id, item_data, company_id)
    return ChangeOrderItemResponse(**{
        k: v for k, v in item.__dict__.items() if not k.startswith('_')
    })


@router.delete(
    "/{change_order_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete change order item"
)
def delete_item(
    change_order_id: UUID,
    item_id: UUID,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """Delete an item from a change order."""
    service.delete_item(change_order_id, item_id, company_id)


# --- Workflow ---

@router.post(
    "/{change_order_id}/accept",
    response_model=ChangeOrderDetailResponse,
    summary="Accept a change order"
)
def accept_change_order(
    change_order_id: UUID,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    accepted_by_user_id: UUID = Query(..., description="User accepting the change order"),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """Accept a change order (must be draft or pending_approval)."""
    change_order = service.accept_change_order(change_order_id, company_id, accepted_by_user_id)
    return ChangeOrderDetailResponse.from_orm_with_details(change_order)


@router.post(
    "/{change_order_id}/reject",
    response_model=ChangeOrderDetailResponse,
    summary="Reject a change order"
)
def reject_change_order(
    change_order_id: UUID,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """Reject a change order."""
    change_order = service.reject_change_order(change_order_id, company_id)
    return ChangeOrderDetailResponse.from_orm_with_details(change_order)


@router.post(
    "/{change_order_id}/apply",
    response_model=ChangeOrderDetailResponse,
    summary="Apply change order to budget"
)
def apply_change_order(
    change_order_id: UUID,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    applied_by_user_id: UUID = Query(..., description="User applying the change order"),
    service: ChangeOrderService = Depends(get_change_order_service)
):
    """
    Apply an accepted change order to its budget.

    This adds the change order items as a new budget category
    and creates a new budget version snapshot.
    """
    change_order = service.apply_change_order(change_order_id, company_id, applied_by_user_id)
    return ChangeOrderDetailResponse.from_orm_with_details(change_order)


# --- PDF Generation ---

@router.get(
    "/{change_order_id}/pdf",
    summary="Generate change order PDF"
)
def generate_pdf(
    change_order_id: UUID,
    company_id: UUID = Query(..., description="Company ID for multi-tenant isolation"),
    service: ChangeOrderService = Depends(get_change_order_service),
    pdf_service: ChangeOrderPDFService = Depends(get_change_order_pdf_service)
):
    """Generate and download a professional Change Order PDF."""
    change_order = service.get_change_order(change_order_id, company_id)
    pdf_bytes = pdf_service.generate_pdf(change_order)

    # Build filename
    project = change_order.project
    client = project.client if project else None

    client_name = (client.name if client else "Client").replace(" ", "_")
    project_name = (project.name if project else "Project").replace(" ", "_")
    timestamp = change_order.created_at.strftime("%Y-%m-%d") if change_order.created_at else ""

    filename = f"ChangeOrder_{change_order.order_number}_{client_name}_{project_name}_{timestamp}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
