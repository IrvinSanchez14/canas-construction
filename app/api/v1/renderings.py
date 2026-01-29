"""
Rendering endpoints with dependency injection, clean architecture, and N+1 optimization.

Provides complete CRUD operations for visual project proposals including:
- Creating and managing renderings
- Managing rendering images (3D renders, material samples)
- Managing rendering items (specifications, pricing)
- Importing items from budgets
- PDF generation (endpoint ready, implementation can be added)
"""

from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from uuid import UUID
from io import BytesIO

from app.core.dependencies import get_rendering_service
from app.services.rendering_service import RenderingService
from app.services.pdf_service import get_rendering_pdf_service, RenderingPDFService
from app.schemas.rendering import (
    RenderingCreate,
    RenderingUpdate,
    RenderingResponse,
    RenderingDetailResponse,
    RenderingImageCreate,
    RenderingImageUpdate,
    RenderingImageResponse,
    RenderingItemCreate,
    RenderingItemUpdate,
    RenderingItemResponse,
    ReorderImagesRequest,
    ImportBudgetItemsRequest,
    SendRenderingRequest
)
from app.models.rendering import RenderingStatus

router = APIRouter(prefix="/renderings", tags=["Renderings"])


# ============== Rendering CRUD ==============

@router.post("/", response_model=RenderingResponse, status_code=status.HTTP_201_CREATED)
def create_rendering(
    rendering: RenderingCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Create a new rendering for a visual project proposal.

    A rendering contains:
    - 3D rendered images (uploaded by admin, created externally in 3D software)
    - Material samples with images
    - Item details with specifications and pricing

    Business rules enforced:
    - If visit_id is provided, visit must exist and belong to the company
    - If budget_id is provided, budget must exist and belong to the company
    - Multi-tenant isolation enforced

    **Workflow Statuses:**
    - DRAFT: Being created/edited (default)
    - SENT: Sent to client
    - APPROVED: Approved by client
    - REJECTED: Rejected by client
    """
    return service.create_rendering(rendering, company_id)


@router.get("/", response_model=List[RenderingResponse])
def list_renderings(
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    visit_id: Optional[UUID] = Query(None, description="Filter by visit ID"),
    budget_id: Optional[UUID] = Query(None, description="Filter by budget ID"),
    status_filter: Optional[RenderingStatus] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Get all renderings with optional filters.

    **IMPORTANT:**
    - company_id is REQUIRED for multi-tenant isolation
    - Can filter by visit, budget, status, or combination

    **Available Statuses:**
    - draft: Being created/edited
    - sent: Sent to client
    - approved: Approved by client
    - rejected: Rejected by client
    """
    return service.get_renderings(
        company_id=company_id,
        visit_id=visit_id,
        budget_id=budget_id,
        status=status_filter,
        skip=skip,
        limit=limit
    )


@router.get("/{rendering_id}", response_model=RenderingDetailResponse)
def get_rendering(
    rendering_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Get a specific rendering by ID with all details.

    Includes:
    - All images (3D renders and material samples)
    - All items with specifications and pricing
    - Related visit and budget information
    """
    rendering = service.get_rendering(rendering_id, company_id)
    return RenderingDetailResponse.from_orm_with_details(rendering)


@router.put("/{rendering_id}", response_model=RenderingDetailResponse)
def update_rendering(
    rendering_id: UUID,
    rendering_update: RenderingUpdate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Update a rendering.

    Can update:
    - Title and description
    - Status
    - Associated visit and budget
    - Client approval information
    """
    rendering = service.update_rendering(rendering_id, rendering_update, company_id)
    return RenderingDetailResponse.from_orm_with_details(rendering)


@router.patch("/{rendering_id}/status", response_model=RenderingDetailResponse)
def change_rendering_status(
    rendering_id: UUID,
    new_status: RenderingStatus = Query(..., description="New status for the rendering"),
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    sent_to_email: Optional[str] = Query(None, description="Email if status is SENT"),
    approved_by: Optional[str] = Query(None, description="Client name if status is APPROVED"),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Change the status of a rendering (workflow management).

    Typical workflow:
    - DRAFT → SENT (send to client)
    - SENT → APPROVED (client approves)
    - SENT → REJECTED (client rejects)
    - REJECTED → DRAFT (revise and try again)

    When changing to SENT, provide sent_to_email.
    When changing to APPROVED, provide approved_by (client name).
    """
    rendering = service.change_status(
        rendering_id, new_status, company_id, sent_to_email, approved_by
    )
    return RenderingDetailResponse.from_orm_with_details(rendering)


@router.delete("/{rendering_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rendering(
    rendering_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Delete a rendering.

    Note: This is a hard delete. All associated images and items will also be deleted.
    """
    service.delete_rendering(rendering_id, company_id)
    return None


# ============== Image Management ==============

@router.post("/{rendering_id}/images", response_model=RenderingImageResponse, status_code=status.HTTP_201_CREATED)
def add_rendering_image(
    rendering_id: UUID,
    image: RenderingImageCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Add an image to a rendering.

    **Image Types:**
    - project: 3D rendered images of the project
    - material: Material sample images

    **Note:** Images are uploaded externally (created in 3D software).
    This endpoint only stores the URL reference.
    """
    return service.add_image(rendering_id, image, company_id)


@router.put("/{rendering_id}/images/{image_id}", response_model=RenderingImageResponse)
def update_rendering_image(
    rendering_id: UUID,
    image_id: UUID,
    image_update: RenderingImageUpdate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """Update an image in a rendering."""
    return service.update_image(rendering_id, image_id, image_update, company_id)


@router.delete("/{rendering_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rendering_image(
    rendering_id: UUID,
    image_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """Delete an image from a rendering."""
    service.delete_image(rendering_id, image_id, company_id)
    return None


@router.post("/{rendering_id}/images/reorder", response_model=List[RenderingImageResponse])
def reorder_rendering_images(
    rendering_id: UUID,
    request: ReorderImagesRequest,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Reorder images in a rendering.

    Provide the image IDs in the desired order.
    All images must belong to the specified rendering.
    """
    return service.reorder_images(rendering_id, request.image_ids, company_id)


# ============== Item Management ==============

@router.post("/{rendering_id}/items", response_model=RenderingItemResponse, status_code=status.HTTP_201_CREATED)
def add_rendering_item(
    rendering_id: UUID,
    item: RenderingItemCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Add an item to a rendering.

    Items include:
    - Category (e.g., "Electrical", "Plumbing")
    - Name and specifications (flexible key-value pairs)
    - Optional image
    - Pricing information

    Subtotal and total are automatically calculated from quantity and unit_price.
    """
    return service.add_item(rendering_id, item, company_id)


@router.put("/{rendering_id}/items/{item_id}", response_model=RenderingItemResponse)
def update_rendering_item(
    rendering_id: UUID,
    item_id: UUID,
    item_update: RenderingItemUpdate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Update an item in a rendering.

    Subtotal and total are automatically recalculated if quantity or unit_price changes.
    """
    return service.update_item(rendering_id, item_id, item_update, company_id)


@router.delete("/{rendering_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rendering_item(
    rendering_id: UUID,
    item_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """Delete an item from a rendering."""
    service.delete_item(rendering_id, item_id, company_id)
    return None


@router.post("/{rendering_id}/items/import", response_model=List[RenderingItemResponse])
def import_budget_items(
    rendering_id: UUID,
    request: ImportBudgetItemsRequest,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service)
):
    """
    Import items from a budget into the rendering.

    This allows reusing budget line items as rendering items.
    Budget items are copied (not linked), so changes to the budget
    won't affect the rendering items.

    If item_ids is not provided, all items from the budget are imported.
    """
    return service.import_budget_items(
        rendering_id=rendering_id,
        budget_id=request.budget_id,
        company_id=company_id,
        item_ids=request.item_ids
    )


# ============== PDF Generation ==============

@router.get("/{rendering_id}/pdf")
def generate_rendering_pdf(
    rendering_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: RenderingService = Depends(get_rendering_service),
    pdf_service: RenderingPDFService = Depends(get_rendering_pdf_service)
):
    """
    Generate a PDF for the rendering.

    The PDF includes:
    - Cover page with project information
    - Full-page 3D rendered images
    - Material samples grid
    - Item details with specifications and pricing
    - Total amount
    """
    rendering = service.get_rendering(rendering_id, company_id)

    # Generate PDF
    pdf_bytes = pdf_service.generate_pdf(rendering)

    # Return as downloadable PDF
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=rendering_{rendering.title.replace(' ', '_')}.pdf"
        }
    )
