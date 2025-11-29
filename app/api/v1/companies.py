"""
Company endpoints with dependency injection and clean architecture.
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_company_service
from app.services import CompanyService
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    company: CompanyCreate,
    service: CompanyService = Depends(get_company_service)
):
    """
    Create a new company.

    Features:
    - Automatic dependency injection
    - Custom exceptions (auto-converted to HTTP responses)
    - Business logic in service layer
    - Data access in repository layer
    """
    return service.create_company(company)


@router.get("/", response_model=List[CompanyResponse])
def list_companies(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    service: CompanyService = Depends(get_company_service)
):
    """
    Get all companies with pagination.

    Supports filtering and will use caching for better performance.
    """
    return service.get_companies(skip=skip, limit=limit, is_active=is_active)


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: UUID,
    service: CompanyService = Depends(get_company_service)
):
    """
    Get a specific company by ID.

    Raises NotFoundException automatically if not found.
    """
    return service.get_company(company_id)


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: UUID,
    company: CompanyUpdate,
    service: CompanyService = Depends(get_company_service)
):
    """
    Update a company.

    Validates business rules in service layer.
    """
    return service.update_company(company_id, company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: UUID,
    service: CompanyService = Depends(get_company_service)
):
    """
    Delete a company (cascade deletes all users and roles).

    Logs warning and performs cascading delete.
    """
    service.delete_company(company_id)


@router.get("/stats/count")
def count_companies(
    is_active: Optional[bool] = Query(None),
    service: CompanyService = Depends(get_company_service)
):
    """
    Count total companies.

    Useful for pagination and dashboards.
    """
    count = service.count_companies(is_active=is_active)
    return {"total": count, "is_active": is_active}
