from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal


class BudgetCategoryBase(BaseModel):
    """Base schema for BudgetCategory."""
    name: str
    description: Optional[str] = None
    images: Optional[List[str]] = None
    order_index: int = Field(default=0, ge=0)

    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        if v and len(v) > 3:
            raise ValueError("Maximum 3 images allowed per category")
        return v

    model_config = ConfigDict(from_attributes=True)


class BudgetCategoryUpdate(BaseModel):
    """Schema for updating a budget category."""
    name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    order_index: Optional[int] = Field(None, ge=0)

    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        if v and len(v) > 3:
            raise ValueError("Maximum 3 images allowed per category")
        return v

    model_config = ConfigDict(from_attributes=True)
