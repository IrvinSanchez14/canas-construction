"""
User endpoints with dependency injection, clean architecture, and N+1 optimization.

🔒 All endpoints require authentication.
"""

from fastapi import APIRouter, Depends, status, Query, HTTPException
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_user_service
from app.core.auth import get_current_active_user, get_current_superuser
from app.models import User
from app.services import UserService
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    current_user: User = Depends(get_current_active_user),  # 🔒 Authentication required
    service: UserService = Depends(get_user_service)
):
    """
    Create a new user for a company.

    🔒 **Authentication Required**

    **Authorization Rules:**
    - Authenticated users can only create users for their own company
    - New user will be created in the authenticated user's company

    **Business rules enforced:**
    - Email must be unique globally
    - Company must exist (automatically set to current user's company)
    - All roles must exist and belong to same company
    - Password automatically hashed before storage

    **Use Case:**
    Admin users can create new employees/users for their company.
    """
    # Enforce multi-tenant isolation: users can only create users for their own company
    if user.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You can only create users for your own company (ID: {current_user.company_id})"
        )

    return service.create_user(user)


@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),  # 🔒 Authentication required
    service: UserService = Depends(get_user_service)
):
    """
    Get all users for your company.

    🔒 **Authentication Required**

    **Authorization:**
    - Automatically filters to show only users from your company
    - Multi-tenant isolation enforced

    **Features:**
    - Roles are eagerly loaded (N+1 query optimization)
    - Uses optimized repository methods

    **Performance:**
    - Without optimization: 1 + N queries (slow)
    - With optimization: 1-2 queries (fast)
    """
    # Automatically filter by current user's company (multi-tenant isolation)
    return service.get_users(
        company_id=current_user.company_id,  # Enforced!
        skip=skip,
        limit=limit,
        is_active=is_active
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),  # 🔒 Authentication required
    service: UserService = Depends(get_user_service)
):
    """
    Get a specific user by ID.

    🔒 **Authentication Required**

    **Authorization:**
    - Can only view users from your own company
    - Multi-tenant isolation enforced

    **Features:**
    - Includes roles with eager loading (optimized)
    """
    # Enforce multi-tenant: can only view users from own company
    return service.get_user(user_id, company_id=current_user.company_id)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    user: UserUpdate,
    current_user: User = Depends(get_current_active_user),  # 🔒 Authentication required
    service: UserService = Depends(get_user_service)
):
    """
    Update a user.

    🔒 **Authentication Required**

    **Authorization:**
    - Can only update users from your own company
    - Multi-tenant isolation enforced

    **Features:**
    - Password automatically hashed if provided
    - Email uniqueness validated
    - Role IDs replace all current roles
    - Validates roles belong to user's company
    """
    # Enforce multi-tenant: can only update users from own company
    return service.update_user(user_id, user, company_id=current_user.company_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),  # 🔒 Authentication required
    service: UserService = Depends(get_user_service)
):
    """
    Delete a user.

    🔒 **Authentication Required**

    **Authorization:**
    - Can only delete users from your own company
    - Multi-tenant isolation enforced
    """
    # Enforce multi-tenant: can only delete users from own company
    service.delete_user(user_id, company_id=current_user.company_id)
    return None
