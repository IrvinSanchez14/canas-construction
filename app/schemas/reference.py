from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class ReferenceBase(BaseModel):
    """Base schema for Reference."""
    client_name: str
    location: str
    project_description: str
    project_value: str
    phone: Optional[str] = None
    display_order: Optional[int] = 0


class ReferenceCreate(ReferenceBase):
    """Schema for creating a new reference."""
    company_id: UUID


class ReferenceUpdate(BaseModel):
    """Schema for updating a reference."""
    client_name: Optional[str] = None
    location: Optional[str] = None
    project_description: Optional[str] = None
    project_value: Optional[str] = None
    phone: Optional[str] = None
    display_order: Optional[int] = None


class ReferenceResponse(ReferenceBase):
    """Schema for reference response."""
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
