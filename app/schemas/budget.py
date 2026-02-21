from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from app.models.budget import BudgetStatus
from app.schemas.category_profit import CategoryProfitResponse


# --- Budget Item Schemas ---

class BudgetItemBase(BaseModel):
    """Base schema for BudgetItem."""
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
    budget_category_id: UUID
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
            **{k: v for k, v in item.__dict__.items() if not k.startswith('_')},
            "catalog_item_name": item.catalog_item.name if item.catalog_item else None,
        }
        return cls(**data)


# --- Budget Category Schemas ---

class BudgetCategoryCreate(BaseModel):
    """Schema for creating a budget category with items."""
    name: str
    description: Optional[str] = None
    images: Optional[List[str]] = None
    order_index: int = Field(default=0, ge=0)
    items: Optional[List[BudgetItemCreate]] = Field(default_factory=list)

    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        if v and len(v) > 3:
            raise ValueError("Maximum 3 images allowed per category")
        return v

    model_config = ConfigDict(from_attributes=True)


class BudgetCategoryDetailResponse(BaseModel):
    """Schema for budget category response with items and profit data."""
    id: UUID
    budget_id: UUID
    name: str
    description: Optional[str] = None
    images: Optional[List[str]] = None
    order_index: int
    subtotal: Decimal
    budget_items: List[BudgetItemDetailResponse] = Field(default_factory=list)
    category_profit: Optional[CategoryProfitResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_details(cls, category):
        data = {
            **{k: v for k, v in category.__dict__.items() if not k.startswith('_')},
            "budget_items": [
                BudgetItemDetailResponse.from_orm_with_details(item)
                for item in category.budget_items
            ],
            "category_profit": (
                CategoryProfitResponse.from_orm_with_details(category.category_profit)
                if category.category_profit else None
            ),
        }
        return cls(**data)


# --- Budget Schemas ---

class BudgetBase(BaseModel):
    """Base schema for Budget."""
    title: str
    description: Optional[str] = None
    status: BudgetStatus = BudgetStatus.DRAFT
    total_amount: Decimal = Field(default=0, decimal_places=2, ge=0)

    model_config = ConfigDict(from_attributes=True)


class BudgetCreate(BudgetBase):
    """Schema for creating a new budget with categories and items."""
    visit_id: UUID
    categories: Optional[List[BudgetCategoryCreate]] = Field(default_factory=list)


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
    current_version: int = 0
    accepted_by_user_id: Optional[UUID] = None
    accepted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetDetailResponse(BudgetResponse):
    """Schema for detailed budget response with categories and items."""
    budget_categories: List[BudgetCategoryDetailResponse] = Field(default_factory=list)
    accepted_by_name: Optional[str] = Field(None, description="Name of user who accepted the budget")
    visit_title: Optional[str] = Field(None)
    project_name: Optional[str] = Field(None)
    project_address: Optional[str] = Field(None)
    client_name: Optional[str] = Field(None)
    client_phone: Optional[str] = Field(None)
    client_email: Optional[str] = Field(None)

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_details(cls, budget):
        """Create response with categories, items, and accepted_by name."""
        project = budget.visit.project if budget.visit else None
        client = project.client if project else None
        data = {
            **{k: v for k, v in budget.__dict__.items() if not k.startswith('_')},
            "budget_categories": [
                BudgetCategoryDetailResponse.from_orm_with_details(cat)
                for cat in budget.budget_categories
            ],
            "accepted_by_name": budget.accepted_by.full_name if budget.accepted_by else None,
            "visit_title": budget.visit.title if budget.visit else None,
            "project_name": project.name if project else None,
            "project_address": project.address if project else None,
            "client_name": client.name if client else None,
            "client_phone": client.phone if client else None,
            "client_email": client.email if client else None,
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
