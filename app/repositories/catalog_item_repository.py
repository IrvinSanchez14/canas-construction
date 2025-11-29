"""Catalog Item Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.models import CatalogItem, UnitType
from app.repositories.base import BaseRepository


class CatalogItemRepository(BaseRepository[CatalogItem]):
    """Repository for CatalogItem entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(CatalogItem, db)

    def get_by_company(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
        unity_filter: Optional[UnitType] = None,
        include_creator: bool = False
    ) -> List[CatalogItem]:
        """
        Get all catalog items for a specific company.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit
            active_only: Filter only active items
            unity_filter: Filter by unit type
            include_creator: Whether to eager load creator (prevents N+1)
        """
        query = self.db.query(CatalogItem).filter(CatalogItem.company_id == company_id)

        if active_only:
            query = query.filter(CatalogItem.is_active == True)

        if unity_filter:
            query = query.filter(CatalogItem.unity == unity_filter)

        if include_creator:
            query = query.options(joinedload(CatalogItem.created_by))

        return query.offset(skip).limit(limit).all()

    def get_by_id_with_creator(self, item_id: UUID) -> Optional[CatalogItem]:
        """Get catalog item by ID with creator eagerly loaded (N+1 optimization)."""
        return self.db.query(CatalogItem).options(
            joinedload(CatalogItem.created_by)
        ).filter(CatalogItem.id == item_id).first()

    def get_by_name(self, name: str, company_id: UUID) -> Optional[CatalogItem]:
        """Get catalog item by name within a company."""
        return self.db.query(CatalogItem).filter(
            CatalogItem.name == name,
            CatalogItem.company_id == company_id
        ).first()

    def exists_by_name(
        self,
        name: str,
        company_id: UUID,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """Check if item name exists within a company."""
        query = self.db.query(CatalogItem.id).filter(
            CatalogItem.name == name,
            CatalogItem.company_id == company_id
        )

        if exclude_id:
            query = query.filter(CatalogItem.id != exclude_id)

        return query.first() is not None

    def get_by_unity(
        self,
        company_id: UUID,
        unity: UnitType,
        active_only: bool = True
    ) -> List[CatalogItem]:
        """Get all items for a company filtered by unit type."""
        query = self.db.query(CatalogItem).filter(
            CatalogItem.company_id == company_id,
            CatalogItem.unity == unity
        )

        if active_only:
            query = query.filter(CatalogItem.is_active == True)

        return query.all()

    def get_by_creator(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[CatalogItem]:
        """Get all items created by a specific user."""
        return self.db.query(CatalogItem).filter(
            CatalogItem.created_by_user_id == user_id
        ).offset(skip).limit(limit).all()

    def count_by_company(self, company_id: UUID, active_only: bool = False) -> int:
        """Count catalog items for a specific company."""
        query = self.db.query(CatalogItem.id).filter(
            CatalogItem.company_id == company_id
        )

        if active_only:
            query = query.filter(CatalogItem.is_active == True)

        return query.count()

    def get_active_items(self, company_id: UUID) -> List[CatalogItem]:
        """Get all active catalog items for a company."""
        return self.db.query(CatalogItem).filter(
            CatalogItem.company_id == company_id,
            CatalogItem.is_active == True
        ).all()
