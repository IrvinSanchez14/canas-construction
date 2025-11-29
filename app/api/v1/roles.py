"""
Role endpoints with dependency injection and clean architecture.
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_role_service
from app.services import RoleService
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role: RoleCreate,
    service: RoleService = Depends(get_role_service)
):
    """
    Create a new role for a company.

    Business rules enforced in service layer:
    - Company must exist
    - Role name must be unique within company
    """
    return service.create_role(role)


@router.get("/", response_model=List[RoleResponse])
def list_roles(
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    service: RoleService = Depends(get_role_service)
):
    """
    Get all roles with optional filters.

    For multi-tenant apps, ALWAYS provide company_id filter.
    """
    return service.get_roles(
        company_id=company_id,
        skip=skip,
        limit=limit,
        is_active=is_active
    )


@router.get("/company/{company_id}/active", response_model=List[RoleResponse])
def list_active_roles_for_company(
    company_id: UUID,
    service: RoleService = Depends(get_role_service)
):
    """
    Get all active roles for a specific company.

    Optimized endpoint for dropdown lists and forms.
    """
    return service.get_active_roles_by_company(company_id)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: RoleService = Depends(get_role_service)
):
    """
    Get a specific role by ID.

    Optionally validates company ownership for security.
    """
    return service.get_role(role_id, company_id)


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: UUID,
    role: RoleUpdate,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: RoleService = Depends(get_role_service)
):
    """
    Update a role.

    Validates role name uniqueness within company.
    """
    return service.update_role(role_id, role, company_id)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: RoleService = Depends(get_role_service)
):
    """
    Delete a role.

    WARNING: This will unassign the role from all users.
    """
    service.delete_role(role_id, company_id)
