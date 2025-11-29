from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from typing import Optional
from uuid import UUID
from decimal import Decimal
from app.models.project import ProjectStatus
from app.schemas.client import ClientResponse
from app.schemas.project_category import ProjectCategoryResponse


class ProjectBase(BaseModel):
    """Base schema for Project."""
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.LEAD
    estimated_budget: Optional[Decimal] = Field(None, decimal_places=2)
    actual_cost: Optional[Decimal] = Field(None, decimal_places=2)
    start_date: Optional[date] = None
    estimated_completion_date: Optional[date] = None
    actual_completion_date: Optional[date] = None
    address: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    client_id: UUID
    category_id: UUID


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    estimated_budget: Optional[Decimal] = Field(None, decimal_places=2)
    actual_cost: Optional[Decimal] = Field(None, decimal_places=2)
    start_date: Optional[date] = None
    estimated_completion_date: Optional[date] = None
    actual_completion_date: Optional[date] = None
    address: Optional[str] = None
    category_id: Optional[UUID] = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: UUID
    client_id: UUID
    category_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDetailResponse(ProjectResponse):
    """Schema for detailed project response with relationships."""
    client: ClientResponse
    category: ProjectCategoryResponse

    model_config = ConfigDict(from_attributes=True)
