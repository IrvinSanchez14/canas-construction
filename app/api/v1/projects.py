"""
Project endpoints with dependency injection, clean architecture, and N+1 optimization.
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_project_service
from app.services import ProjectService
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse
)
from app.models.project import ProjectStatus

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    company_id: UUID = Query(..., description="Company ID (REQUIRED for validation)"),
    service: ProjectService = Depends(get_project_service)
):
    """
    Create a new project.

    Business rules enforced:
    - Client must exist and belong to the company
    - Category must exist and belong to the company
    - Multi-tenant isolation enforced
    """
    return service.create_project(project, company_id)


@router.get("/", response_model=List[ProjectDetailResponse])
def list_projects(
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[ProjectStatus] = Query(None, alias="status", description="Filter by project status"),
    category_id: Optional[UUID] = Query(None, description="Filter by category ID"),
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    include_details: bool = Query(True, description="Include client and category details"),
    service: ProjectService = Depends(get_project_service)
):
    """
    Get all projects for a company with optional filters.

    **IMPORTANT for CRM:**
    - company_id is REQUIRED for multi-tenant isolation
    - Client and category are eagerly loaded (N+1 query optimization)
    - Can filter by status, category, or client
    - Uses optimized repository methods

    **Performance:**
    - Without optimization: 1 + N queries (slow)
    - With optimization: 1-2 queries (fast)

    **Available Statuses:**
    - lead: Initial lead/prospect
    - quoted: Quote has been sent
    - approved: Project approved by client
    - in_progress: Work in progress
    - completed: Project finished
    - cancelled: Project cancelled
    - on_hold: Temporarily paused
    """
    return service.get_projects(
        company_id=company_id,
        skip=skip,
        limit=limit,
        status=status_filter,
        category_id=category_id,
        client_id=client_id,
        include_details=include_details
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ProjectService = Depends(get_project_service)
):
    """
    Get a specific project by ID.

    Includes client and category with eager loading (optimized).
    Validates company ownership if company_id provided.
    """
    return service.get_project(project_id, company_id, include_details=True)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    project: ProjectUpdate,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ProjectService = Depends(get_project_service)
):
    """
    Update a project.

    Features:
    - Validates company ownership if company_id provided
    - If changing category, validates new category belongs to same company
    - Only updates fields that are provided
    """
    return service.update_project(project_id, project, company_id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ProjectService = Depends(get_project_service)
):
    """
    Delete a project.
    """
    service.delete_project(project_id, company_id)
    return None


@router.get("/by-status/{status}", response_model=List[ProjectDetailResponse])
def get_projects_by_status(
    status: ProjectStatus,
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ProjectService = Depends(get_project_service)
):
    """
    Get projects filtered by specific status.

    Useful for:
    - Dashboard views (active projects, leads, etc.)
    - Status-specific reports
    - Pipeline management
    """
    return service.get_projects_by_status(
        company_id=company_id,
        status=status,
        skip=skip,
        limit=limit
    )
