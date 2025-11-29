"""
Project Category endpoints with dependency injection and clean architecture.
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_project_category_service
from app.services import ProjectCategoryService
from app.schemas.project_category import (
    ProjectCategoryCreate,
    ProjectCategoryUpdate,
    ProjectCategoryResponse
)

router = APIRouter(prefix="/project-categories", tags=["Project Categories"])


@router.post("/", response_model=ProjectCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_project_category(
    category: ProjectCategoryCreate,
    service: ProjectCategoryService = Depends(get_project_category_service)
):
    """
    Create a new project category for a company.

    Business rules enforced:
    - Company must exist
    - Category name must be unique within company
    - Multi-tenant isolation enforced
    """
    return service.create_project_category(category)


@router.post("/seed", response_model=List[ProjectCategoryResponse], status_code=status.HTTP_201_CREATED)
def seed_default_categories(
    company_id: UUID = Query(..., description="Company ID to seed categories for"),
    service: ProjectCategoryService = Depends(get_project_category_service)
):
    """
    Seed default project categories for a company.

    Creates default categories:
    - Kitchen
    - Bathroom
    - Outside
    - Other

    Only creates categories that don't already exist.
    Useful for initializing a new company's categories.
    """
    return service.seed_default_categories(company_id)


@router.get("/", response_model=List[ProjectCategoryResponse])
def list_project_categories(
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False, description="Filter only active categories"),
    service: ProjectCategoryService = Depends(get_project_category_service)
):
    """
    Get all project categories for a company.

    **IMPORTANT for CRM:**
    - company_id is REQUIRED for multi-tenant isolation
    - Can filter to show only active categories
    """
    return service.get_project_categories(
        company_id=company_id,
        skip=skip,
        limit=limit,
        active_only=active_only
    )


@router.get("/{category_id}", response_model=ProjectCategoryResponse)
def get_project_category(
    category_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ProjectCategoryService = Depends(get_project_category_service)
):
    """
    Get a specific project category by ID.

    Validates company ownership if company_id provided.
    """
    return service.get_project_category(category_id, company_id)


@router.put("/{category_id}", response_model=ProjectCategoryResponse)
def update_project_category(
    category_id: UUID,
    category: ProjectCategoryUpdate,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ProjectCategoryService = Depends(get_project_category_service)
):
    """
    Update a project category.

    Features:
    - Validates company ownership if company_id provided
    - Category name must remain unique within company
    - Only updates fields that are provided
    """
    return service.update_project_category(category_id, category, company_id)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_category(
    category_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ProjectCategoryService = Depends(get_project_category_service)
):
    """
    Delete a project category.

    WARNING: This will fail if there are projects using this category
    due to RESTRICT constraint. Update projects to a different category first.
    """
    service.delete_project_category(category_id, company_id)
    return None
