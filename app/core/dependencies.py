"""
Dependency Injection Container following SOLID principles.

This module provides factory functions for creating service instances
with all their dependencies properly injected.

Benefits:
- Centralized dependency management
- Easy to mock for testing
- Follows Dependency Inversion Principle
- Loose coupling between components
"""

from functools import lru_cache
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import (
    CompanyRepository,
    RoleRepository,
    UserRepository,
    ClientRepository,
    ProjectCategoryRepository,
    ProjectRepository,
    CatalogItemRepository
)
from app.services import (
    CompanyService,
    RoleService,
    UserService,
    ClientService,
    ProjectCategoryService,
    ProjectService,
    CatalogItemService
)
from app.core.password import PasswordHasher, password_hasher


# Repository Factories

def get_company_repository(db: Session = Depends(get_db)) -> CompanyRepository:
    """Get Company repository instance."""
    return CompanyRepository(db)


def get_role_repository(db: Session = Depends(get_db)) -> RoleRepository:
    """Get Role repository instance."""
    return RoleRepository(db)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """Get User repository instance."""
    return UserRepository(db)


# Service Factories

def get_company_service(db: Session = Depends(get_db)) -> CompanyService:
    """
    Get CompanyService with all dependencies injected.

    Args:
        db: Database session

    Returns:
        Fully configured CompanyService instance
    """
    repository = get_company_repository(db)
    return CompanyService(repository=repository)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """
    Get UserService with all dependencies injected.

    Args:
        db: Database session

    Returns:
        Fully configured UserService instance
    """
    user_repo = get_user_repository(db)
    company_repo = get_company_repository(db)
    role_repo = get_role_repository(db)

    return UserService(
        user_repository=user_repo,
        company_repository=company_repo,
        role_repository=role_repo,
        password_hasher=password_hasher  # Singleton instance
    )


def get_role_service(db: Session = Depends(get_db)) -> RoleService:
    """
    Get RoleService with all dependencies injected.

    Args:
        db: Database session

    Returns:
        Fully configured RoleService instance
    """
    role_repo = get_role_repository(db)
    company_repo = get_company_repository(db)

    return RoleService(
        role_repository=role_repo,
        company_repository=company_repo
    )


@lru_cache()
def get_password_hasher() -> PasswordHasher:
    """
    Get PasswordHasher instance (singleton).

    Returns:
        PasswordHasher instance
    """
    return password_hasher


# New CRM Repository Factories

def get_client_repository(db: Session = Depends(get_db)) -> ClientRepository:
    """Get Client repository instance."""
    return ClientRepository(db)


def get_project_category_repository(db: Session = Depends(get_db)) -> ProjectCategoryRepository:
    """Get ProjectCategory repository instance."""
    return ProjectCategoryRepository(db)


def get_project_repository(db: Session = Depends(get_db)) -> ProjectRepository:
    """Get Project repository instance."""
    return ProjectRepository(db)


# New CRM Service Factories

def get_client_service(db: Session = Depends(get_db)) -> ClientService:
    """
    Get ClientService with all dependencies injected.

    Args:
        db: Database session

    Returns:
        Fully configured ClientService instance
    """
    client_repo = get_client_repository(db)
    company_repo = get_company_repository(db)

    return ClientService(
        client_repository=client_repo,
        company_repository=company_repo
    )


def get_project_category_service(db: Session = Depends(get_db)) -> ProjectCategoryService:
    """
    Get ProjectCategoryService with all dependencies injected.

    Args:
        db: Database session

    Returns:
        Fully configured ProjectCategoryService instance
    """
    category_repo = get_project_category_repository(db)
    company_repo = get_company_repository(db)

    return ProjectCategoryService(
        project_category_repository=category_repo,
        company_repository=company_repo
    )


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    """
    Get ProjectService with all dependencies injected.

    Args:
        db: Database session

    Returns:
        Fully configured ProjectService instance
    """
    project_repo = get_project_repository(db)
    client_repo = get_client_repository(db)
    category_repo = get_project_category_repository(db)
    user_repo = get_user_repository(db)

    return ProjectService(
        project_repository=project_repo,
        client_repository=client_repo,
        project_category_repository=category_repo,
        user_repository=user_repo
    )


def get_catalog_item_repository(db: Session = Depends(get_db)) -> CatalogItemRepository:
    """Get CatalogItem repository instance."""
    return CatalogItemRepository(db)


def get_catalog_item_service(db: Session = Depends(get_db)) -> CatalogItemService:
    """
    Get CatalogItemService with all dependencies injected.

    Args:
        db: Database session

    Returns:
        Fully configured CatalogItemService instance
    """
    catalog_item_repo = get_catalog_item_repository(db)
    company_repo = get_company_repository(db)
    user_repo = get_user_repository(db)

    return CatalogItemService(
        catalog_item_repository=catalog_item_repo,
        company_repository=company_repo,
        user_repository=user_repo
    )
