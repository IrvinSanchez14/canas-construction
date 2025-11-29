from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class ProjectCategoryBase(BaseModel):
    """Base schema for ProjectCategory."""
    name: str
    description: Optional[str] = None
    is_active: bool = True


class ProjectCategoryCreate(ProjectCategoryBase):
    """Schema for creating a new project category."""
    company_id: UUID


class ProjectCategoryUpdate(BaseModel):
    """Schema for updating a project category."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectCategoryResponse(ProjectCategoryBase):
    """Schema for project category response."""
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
