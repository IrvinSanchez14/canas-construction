"""
Reference endpoints with dependency injection and clean architecture.
"""

from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from uuid import UUID
from io import BytesIO
from datetime import datetime

from app.core.dependencies import get_reference_service
from app.services import ReferenceService
from app.services.reference_pdf_service import get_reference_pdf_service, ReferencePDFService
from app.schemas.reference import ReferenceCreate, ReferenceUpdate, ReferenceResponse

router = APIRouter(prefix="/references", tags=["References"])


@router.post("/", response_model=ReferenceResponse, status_code=status.HTTP_201_CREATED)
def create_reference(
    reference: ReferenceCreate,
    service: ReferenceService = Depends(get_reference_service)
):
    """
    Create a new reference for a company.

    Business rules enforced:
    - Company must exist
    - Multi-tenant isolation enforced
    """
    return service.create_reference(reference)


@router.get("/", response_model=List[ReferenceResponse])
def list_references(
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ReferenceService = Depends(get_reference_service)
):
    """
    Get all references for a company.

    **IMPORTANT for CRM:**
    - company_id is REQUIRED for multi-tenant isolation
    - Results ordered by display_order
    """
    return service.get_references(
        company_id=company_id,
        skip=skip,
        limit=limit
    )


@router.get("/pdf")
def generate_references_pdf(
    company_id: UUID = Query(..., description="Company ID (REQUIRED)"),
    service: ReferenceService = Depends(get_reference_service),
    pdf_service: ReferencePDFService = Depends(get_reference_pdf_service)
):
    """
    Generate a PDF of customer references for a company.

    The PDF includes:
    - Cover page with branding
    - References list page with all customer references
    """
    references = service.get_references(company_id=company_id, skip=0, limit=1000)

    pdf_bytes = pdf_service.generate_pdf(references)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"customer_references_{timestamp}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/{reference_id}", response_model=ReferenceResponse)
def get_reference(
    reference_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ReferenceService = Depends(get_reference_service)
):
    """
    Get a specific reference by ID.

    Validates company ownership if company_id provided.
    """
    return service.get_reference(reference_id, company_id)


@router.put("/{reference_id}", response_model=ReferenceResponse)
def update_reference(
    reference_id: UUID,
    reference: ReferenceUpdate,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ReferenceService = Depends(get_reference_service)
):
    """
    Update a reference.

    Features:
    - Validates company ownership if company_id provided
    - Only updates fields that are provided
    """
    return service.update_reference(reference_id, reference, company_id)


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(
    reference_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ReferenceService = Depends(get_reference_service)
):
    """
    Delete a reference.
    """
    service.delete_reference(reference_id, company_id)
    return None
