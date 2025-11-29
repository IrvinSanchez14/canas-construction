"""
User endpoints with dependency injection, clean architecture, and N+1 optimization.
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_user_service
from app.services import UserService
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserLogin

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    service: UserService = Depends(get_user_service)
):
    """
    Create a new user for a company.

    Business rules enforced:
    - Email must be unique globally
    - Company must exist
    - All roles must exist and belong to same company
    - Password automatically hashed before storage
    """
    return service.create_user(user)


@router.get("/", response_model=List[UserResponse])
def list_users(
    company_id: Optional[UUID] = Query(None, description="Filter by company ID (RECOMMENDED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    service: UserService = Depends(get_user_service)
):
    """
    Get all users with optional filters.

    **IMPORTANT for CRM:**
    - Roles are eagerly loaded (N+1 query optimization)
    - Always filter by company_id for multi-tenant apps
    - Uses optimized repository methods

    **Performance:**
    - Without optimization: 1 + N queries (slow)
    - With optimization: 1-2 queries (fast)
    """
    return service.get_users(
        company_id=company_id,
        skip=skip,
        limit=limit,
        is_active=is_active
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: UserService = Depends(get_user_service)
):
    """
    Get a specific user by ID.

    Includes roles with eager loading (optimized).
    Validates company ownership if company_id provided.
    """
    return service.get_user(user_id, company_id)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    user: UserUpdate,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: UserService = Depends(get_user_service)
):
    """
    Update a user.

    Features:
    - Password automatically hashed if provided
    - Email uniqueness validated
    - Role IDs replace all current roles
    - Validates roles belong to user's company
    """
    return service.update_user(user_id, user, company_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    service: UserService = Depends(get_user_service)
):
    """
    Delete a user.

    Validates company ownership if company_id provided.
    """
    service.delete_user(user_id, company_id)


@router.post("/login", response_model=UserResponse)
def login(
    credentials: UserLogin,
    service: UserService = Depends(get_user_service)
):
    """
    Authenticate a user with email and password.

    **Current:** Returns user object
    **TODO:** Return JWT token instead (coming in JWT implementation)

    Validates:
    - User exists
    - Password matches
    - User is active
    """
    return service.authenticate_user(credentials.email, credentials.password)
