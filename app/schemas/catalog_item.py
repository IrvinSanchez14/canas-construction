from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from decimal import Decimal
from app.models.catalog_item import UnitType


class CatalogItemBase(BaseModel):
    """Base schema for CatalogItem."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    unity: UnitType
    price_base: Decimal = Field(..., decimal_places=2, gt=0, description="Base price must be greater than 0")
    is_active: bool = True


class CatalogItemCreate(CatalogItemBase):
    """
    Schema for creating a new catalog item.

    Note: company_id and created_by_user_id will be set by the service layer
    based on authentication context.
    """
    company_id: UUID
    created_by_user_id: Optional[UUID] = None  # Will be set by service if not provided


class CatalogItemUpdate(BaseModel):
    """Schema for updating a catalog item."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    unity: Optional[UnitType] = None
    price_base: Optional[Decimal] = Field(None, decimal_places=2, gt=0)
    is_active: Optional[bool] = None


class CatalogItemResponse(CatalogItemBase):
    """Schema for catalog item response."""
    id: UUID
    company_id: UUID
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CatalogItemDetailResponse(CatalogItemResponse):
    """
    Schema for detailed catalog item response with creator information.

    Useful for audit trails showing who created each item.
    """
    created_by_name: Optional[str] = Field(None, description="Full name of the user who created this item")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_creator(cls, catalog_item):
        """Create response with creator's full name."""
        data = {
            **catalog_item.__dict__,
            "created_by_name": catalog_item.created_by.full_name if catalog_item.created_by else None
        }
        return cls(**data)
