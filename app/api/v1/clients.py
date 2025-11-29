"""
Client endpoints with dependency injection, clean architecture, and N+1 optimization.
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_client_service
from app.services import ClientService
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client: ClientCreate,
    service: ClientService = Depends(get_client_service)
):
    """
    Create a new client for a company.

    Business rules enforced:
    - Company must exist
    - Multi-tenant isolation enforced
    """
    return service.create_client(client)


@router.get("/", response_model=List[ClientResponse])
def list_clients(
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_projects: bool = Query(False, description="Include client projects"),
    service: ClientService = Depends(get_client_service)
):
    """
    Get all clients for a company.

    **IMPORTANT for CRM:**
    - company_id is REQUIRED for multi-tenant isolation
    - Projects can be eagerly loaded (N+1 query optimization)
    - Uses optimized repository methods

    **Performance:**
    - Without optimization: 1 + N queries (slow)
    - With optimization: 1-2 queries (fast)
    """
    return service.get_clients(
        company_id=company_id,
        skip=skip,
        limit=limit,
        include_projects=include_projects
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ClientService = Depends(get_client_service)
):
    """
    Get a specific client by ID.

    Includes projects with eager loading (optimized).
    Validates company ownership if company_id provided.
    """
    return service.get_client(client_id, company_id)


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: UUID,
    client: ClientUpdate,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ClientService = Depends(get_client_service)
):
    """
    Update a client.

    Features:
    - Validates company ownership if company_id provided
    - Only updates fields that are provided
    """
    return service.update_client(client_id, client, company_id)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: ClientService = Depends(get_client_service)
):
    """
    Delete a client.

    WARNING: This will also delete all projects associated with this client
    due to CASCADE constraint.
    """
    service.delete_client(client_id, company_id)
    return None
