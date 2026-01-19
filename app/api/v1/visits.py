"""
Visit endpoints with dependency injection, clean architecture, and N+1 optimization.

Provides complete CRUD operations for project visits including:
- Creating visits to gather project information
- Updating visit data (images, items, prices)
- Changing visit status (workflow management)
- Retrieving visits with filtering
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_visit_service
from app.services import VisitService
from app.schemas.visit import (
    VisitCreate,
    VisitUpdate,
    VisitResponse,
    VisitDetailResponse,
    VisitListResponse
)
from app.models.visit import VisitStatus

router = APIRouter(prefix="/visits", tags=["Visits"])


@router.post("/", response_model=VisitResponse, status_code=status.HTTP_201_CREATED)
def create_visit(
    visit: VisitCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    created_by_user_id: Optional[UUID] = Query(None, description="User ID who is creating this visit (for audit trail)"),
    service: VisitService = Depends(get_visit_service)
):
    """
    Create a new visit for a project.

    A visit is used to gather and document information about a construction project including:
    - Project details and images
    - Cost estimates (materials, labor)
    - Items identified during the visit
    - Inspection notes

    Business rules enforced:
    - Project must exist and belong to the company
    - Creator user must belong to the company
    - Multi-tenant isolation enforced
    - Total cost is automatically calculated if both materials and labor costs provided

    **Workflow Statuses:**
    - PLANNING: Initial data collection (default)
    - IN_REVIEW: Engineering reviewing the visit data
    - INSPECTION_REQUIRED: Additional inspection needed
    - APPROVED: Visit approved for planning phase
    - VISITED: Visit completed

    **Audit Trail:**
    - Tracks which user created the visit via created_by_user_id
    """
    return service.create_visit(visit, company_id, created_by_user_id)


@router.get("/", response_model=List[VisitDetailResponse])
def list_visits(
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    status_filter: Optional[VisitStatus] = Query(None, alias="status", description="Filter by visit status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_details: bool = Query(True, description="Include project and user details"),
    service: VisitService = Depends(get_visit_service)
):
    """
    Get all visits with optional filters.

    **IMPORTANT for CRM:**
    - company_id is REQUIRED for multi-tenant isolation
    - Can filter by project, status, or both
    - Project and creator details are eagerly loaded (N+1 query optimization)

    **Performance:**
    - Without optimization: 1 + N queries (slow)
    - With optimization: 1-2 queries (fast)

    **Available Statuses:**
    - planning: Initial data collection
    - in_review: Engineering reviewing the visit
    - approved: Visit approved for planning
    - inspection_required: Additional inspection needed
    - visited: Visit completed
    """
    visits = service.get_visits(
        company_id=company_id,
        project_id=project_id,
        status=status_filter,
        skip=skip,
        limit=limit,
        include_details=include_details
    )

    # Convert to detail response with creator names
    return [VisitDetailResponse.from_orm_with_details(visit) for visit in visits]


@router.get("/{visit_id}", response_model=VisitDetailResponse)
def get_visit(
    visit_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: VisitService = Depends(get_visit_service)
):
    """
    Get a specific visit by ID.

    Includes all details with creator and editor information for full audit trail.
    """
    visit = service.get_visit(visit_id, company_id)
    return VisitDetailResponse.from_orm_with_details(visit)


@router.put("/{visit_id}", response_model=VisitDetailResponse)
def update_visit(
    visit_id: UUID,
    visit_update: VisitUpdate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    edited_by_user_id: Optional[UUID] = Query(None, description="User ID who is editing this visit (for audit trail)"),
    service: VisitService = Depends(get_visit_service)
):
    """
    Update a visit.

    Can update:
    - Title and description
    - Visit date and inspection notes
    - Cost estimates (materials, labor, total)
    - Images and attachments
    - Items collected during visit
    - Visit status (workflow management)

    **Audit Trail:**
    - Tracks which user edited the visit via edited_by_user_id
    - Preserves original creator information
    """
    visit = service.update_visit(visit_id, visit_update, company_id, edited_by_user_id)
    return VisitDetailResponse.from_orm_with_details(visit)


@router.patch("/{visit_id}/status", response_model=VisitDetailResponse)
def change_visit_status(
    visit_id: UUID,
    new_status: VisitStatus = Query(..., description="New status for the visit"),
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    reviewed_by_user_id: Optional[UUID] = Query(None, description="User ID who reviewed/approved this status change"),
    service: VisitService = Depends(get_visit_service)
):
    """
    Change the status of a visit (workflow management).

    Typical workflow:
    - PLANNING → IN_REVIEW (submit for engineering review)
    - IN_REVIEW → INSPECTION_REQUIRED (needs more info/inspection)
    - IN_REVIEW → APPROVED (approved for planning phase)
    - APPROVED → VISITED (visit completed and closed)

    This endpoint manages the construction workflow process.
    """
    visit = service.change_visit_status(visit_id, new_status, company_id, reviewed_by_user_id)
    return VisitDetailResponse.from_orm_with_details(visit)


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visit(
    visit_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: VisitService = Depends(get_visit_service)
):
    """
    Delete a visit.

    Note: This is a hard delete. Consider using status changes instead for audit trail.
    """
    service.delete_visit(visit_id, company_id)
    return None


@router.get("/project/{project_id}/pending-reviews", response_model=List[VisitDetailResponse])
def get_pending_reviews(
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: VisitService = Depends(get_visit_service)
):
    """
    Get visits pending engineering review.

    Returns visits in PLANNING or INSPECTION_REQUIRED status.
    Useful for engineering team to see what needs review.
    """
    visits = service.get_pending_reviews(company_id, skip, limit)
    return [VisitDetailResponse.from_orm_with_details(visit) for visit in visits]


@router.get("/project/{project_id}/summary")
def get_project_visits_summary(
    project_id: UUID,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: VisitService = Depends(get_visit_service)
):
    """
    Get summary statistics for a project's visits.

    Returns:
    - Total number of visits
    - Count of visits by status
    """
    return service.get_project_visits_summary(project_id, company_id)
