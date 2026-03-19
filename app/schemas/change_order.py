"""
Change Order Schemas

Pydantic models for ChangeOrder validation and serialization.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from app.models.change_order import ChangeOrderStatus


# --- Change Order Item Schemas ---

class ChangeOrderItemBase(BaseModel):
    """Base schema for ChangeOrderItem."""
    item_code: Optional[str] = None
    description: str
    unit: Optional[str] = None
    quantity: Decimal = Field(..., decimal_places=2, gt=0)
    unit_price: Decimal = Field(..., decimal_places=2, ge=0)
    subtotal: Optional[Decimal] = Field(None, decimal_places=2)
    order_index: int = Field(default=0, ge=0)

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


class ChangeOrderItemCreate(ChangeOrderItemBase):
    """Schema for creating a new change order item."""
    pass


class ChangeOrderItemUpdate(BaseModel):
    """Schema for updating a change order item."""
    item_code: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, decimal_places=2, gt=0)
    unit_price: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    subtotal: Optional[Decimal] = Field(None, decimal_places=2)
    order_index: Optional[int] = Field(None, ge=0)

    model_config = ConfigDict(from_attributes=True)


class ChangeOrderItemResponse(ChangeOrderItemBase):
    """Schema for change order item response."""
    id: UUID
    change_order_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Change Order Schemas ---

class ChangeOrderBase(BaseModel):
    """Base schema for ChangeOrder."""
    title: str
    description: Optional[str] = None
    observations: Optional[List[str]] = None
    status: ChangeOrderStatus = ChangeOrderStatus.DRAFT
    total_amount: Decimal = Field(default=0, decimal_places=2, ge=0)

    model_config = ConfigDict(from_attributes=True)


class ChangeOrderCreate(ChangeOrderBase):
    """Schema for creating a new change order with items."""
    project_id: UUID
    items: Optional[List[ChangeOrderItemCreate]] = Field(default_factory=list)


class ChangeOrderUpdate(BaseModel):
    """Schema for updating a change order."""
    title: Optional[str] = None
    description: Optional[str] = None
    observations: Optional[List[str]] = None
    status: Optional[ChangeOrderStatus] = None

    model_config = ConfigDict(from_attributes=True)


class ChangeOrderResponse(ChangeOrderBase):
    """Schema for change order response."""
    id: UUID
    project_id: UUID
    order_number: int
    accepted_by_user_id: Optional[UUID] = None
    accepted_at: Optional[datetime] = None
    applied_by_user_id: Optional[UUID] = None
    applied_at: Optional[datetime] = None
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChangeOrderDetailResponse(ChangeOrderResponse):
    """Schema for detailed change order response with items and context."""
    change_order_items: List[ChangeOrderItemResponse] = Field(default_factory=list)
    accepted_by_name: Optional[str] = None
    applied_by_name: Optional[str] = None
    created_by_name: Optional[str] = None
    # Project context for PDF
    project_name: Optional[str] = None
    project_address: Optional[str] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_details(cls, change_order):
        """Create response with items and context."""
        project = change_order.project
        client = project.client if project else None

        data = {
            **{k: v for k, v in change_order.__dict__.items() if not k.startswith('_')},
            "change_order_items": [
                ChangeOrderItemResponse(**{
                    k: v for k, v in item.__dict__.items() if not k.startswith('_')
                })
                for item in change_order.change_order_items
            ],
            "accepted_by_name": change_order.accepted_by.full_name if change_order.accepted_by else None,
            "applied_by_name": change_order.applied_by.full_name if change_order.applied_by else None,
            "created_by_name": change_order.created_by.full_name if change_order.created_by else None,
            "project_name": project.name if project else None,
            "project_address": project.address if project else None,
            "client_name": client.name if client else None,
            "client_phone": client.phone if client else None,
            "client_email": client.email if client else None,
        }
        return cls(**data)


class ChangeOrderListResponse(BaseModel):
    """Schema for change order list response with pagination."""
    change_orders: List[ChangeOrderDetailResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)
