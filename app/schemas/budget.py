from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from app.models.budget import BudgetStatus


class BudgetItemBase(BaseModel):
    """Base schema for BudgetItem."""
    section_name: Optional[str] = None
    description: str
    unit: Optional[str] = None
    quantity: Decimal = Field(..., decimal_places=2, gt=0)
    unit_price: Decimal = Field(..., decimal_places=2, ge=0)
    subtotal: Optional[Decimal] = Field(None, decimal_places=2)
    order_index: int = Field(default=0, ge=0)
    catalog_item_id: Optional[UUID] = None

    @model_validator(mode='before')
    @classmethod
    def calculate_subtotal(cls, data):
        """Auto-calculate subtotal if not provided."""
        if isinstance(data, dict) and data.get('subtotal') is None:
            quantity = data.get('quantity')
            unit_price = data.get('unit_price')
            if quantity is not None and unit_price is not None:
                data['subtotal'] = Decimal(str(quantity)) * Decimal(str(unit_price))
        return data

    model_config = ConfigDict(from_attributes=True)


class BudgetItemCreate(BudgetItemBase):
    """Schema for creating a new budget item."""
    pass


class BudgetItemUpdate(BaseModel):
    """Schema for updating a budget item."""
    section_name: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, decimal_places=2, gt=0)
    unit_price: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    subtotal: Optional[Decimal] = Field(None, decimal_places=2)
    order_index: Optional[int] = Field(None, ge=0)
    catalog_item_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class BudgetItemResponse(BudgetItemBase):
    """Schema for budget item response."""
    id: UUID
    budget_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetItemDetailResponse(BudgetItemResponse):
    """Schema for budget item response with catalog item details."""
    catalog_item_name: Optional[str] = Field(None, description="Name of catalog item if referenced")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_details(cls, item):
        """Create response with catalog item name."""
        data = {
            **item.__dict__,
            "catalog_item_name": item.catalog_item.name if item.catalog_item else None,
        }
        return cls(**data)


class BudgetBase(BaseModel):
    """Base schema for Budget."""
    title: str
    description: Optional[str] = None
    status: BudgetStatus = BudgetStatus.DRAFT
    total_amount: Decimal = Field(default=0, decimal_places=2, ge=0)

    model_config = ConfigDict(from_attributes=True)


class BudgetCreate(BudgetBase):
    """Schema for creating a new budget."""
    visit_id: UUID
    budget_items: Optional[List[BudgetItemCreate]] = Field(default_factory=list)


class BudgetUpdate(BaseModel):
    """Schema for updating a budget."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[BudgetStatus] = None
    total_amount: Optional[Decimal] = Field(None, decimal_places=2, ge=0)

    model_config = ConfigDict(from_attributes=True)


class BudgetResponse(BudgetBase):
    """Schema for budget response."""
    id: UUID
    visit_id: UUID
    accepted_by_user_id: Optional[UUID] = None
    accepted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetDetailResponse(BudgetResponse):
    """Schema for detailed budget response with items."""
    budget_items: List[BudgetItemDetailResponse] = Field(default_factory=list)
    accepted_by_name: Optional[str] = Field(None, description="Name of user who accepted the budget")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_details(cls, budget):
        """Create response with items and accepted_by name."""
        data = {
            **budget.__dict__,
            "budget_items": [
                BudgetItemDetailResponse.from_orm_with_details(item)
                for item in budget.budget_items
            ],
            "accepted_by_name": budget.accepted_by.full_name if budget.accepted_by else None,
        }
        return cls(**data)


class BudgetAcceptRequest(BaseModel):
    """Schema for accepting a budget."""
    accepted_by_user_id: UUID

    model_config = ConfigDict(from_attributes=True)


class BudgetListResponse(BaseModel):
    """Schema for budget list response with pagination info."""
    budgets: List[BudgetDetailResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)
