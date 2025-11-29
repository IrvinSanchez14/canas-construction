from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class RoleBase(BaseModel):
    """Base schema for Role."""
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Schema for creating a new role."""
    company_id: UUID


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    """Schema for role response."""
    id: UUID
    company_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
