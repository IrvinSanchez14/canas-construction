from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class ClientBase(BaseModel):
    """Base schema for Client."""
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class ClientCreate(ClientBase):
    """Schema for creating a new client."""
    company_id: UUID


class ClientUpdate(BaseModel):
    """Schema for updating a client."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class ClientResponse(ClientBase):
    """Schema for client response."""
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
