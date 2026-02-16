"""
Category Profit Schemas

Pydantic models for CategoryProfit validation and serialization.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime
from typing import Optional
from uuid import UUID
from decimal import Decimal


class CategoryProfitBase(BaseModel):
    """Base schema for CategoryProfit."""
    provider_price: Decimal = Field(..., decimal_places=2, ge=0)
    delivery_cost: Decimal = Field(default=Decimal("0"), decimal_places=2, ge=0)
    profit_percentage: Decimal = Field(..., decimal_places=2, ge=0)

    model_config = ConfigDict(from_attributes=True)


class CategoryProfitCreate(CategoryProfitBase):
    """Schema for creating/setting category profit data."""
    total_price: Optional[Decimal] = Field(None, decimal_places=2)

    @model_validator(mode='before')
    @classmethod
    def calculate_total_price(cls, data):
        """Auto-calculate total_price from cost components."""
        if isinstance(data, dict):
            provider_price = Decimal(str(data.get('provider_price', 0)))
            delivery_cost = Decimal(str(data.get('delivery_cost', 0)))
            profit_percentage = Decimal(str(data.get('profit_percentage', 0)))
            data['total_price'] = (
                (provider_price + delivery_cost)
                * (1 + profit_percentage / 100)
            ).quantize(Decimal('0.01'))
        return data

    model_config = ConfigDict(from_attributes=True)


class CategoryProfitUpdate(BaseModel):
    """Schema for updating category profit data (partial)."""
    provider_price: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    delivery_cost: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    profit_percentage: Optional[Decimal] = Field(None, decimal_places=2, ge=0)

    model_config = ConfigDict(from_attributes=True)


class CategoryProfitResponse(CategoryProfitBase):
    """Schema for category profit response."""
    id: UUID
    budget_category_id: UUID
    total_price: Decimal
    created_by_user_id: Optional[UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_details(cls, profit):
        """Create response with creator name."""
        data = {
            **profit.__dict__,
            "created_by_name": (
                profit.created_by.full_name if profit.created_by else None
            ),
        }
        return cls(**data)
