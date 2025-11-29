from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class CompanyBase(BaseModel):
    """Base schema for Company."""
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None


class CompanyCreate(CompanyBase):
    """Schema for creating a new company."""
    pass


class CompanyUpdate(BaseModel):
    """Schema for updating a company."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyResponse(CompanyBase):
    """Schema for company response."""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
