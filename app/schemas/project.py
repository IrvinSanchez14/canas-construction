from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from typing import Optional
from uuid import UUID
from app.models.project import ProjectStatus
from app.schemas.client import ClientResponse
from app.schemas.project_category import ProjectCategoryResponse


class ProjectBase(BaseModel):
    """Base schema for Project."""
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.LEAD
    start_date: Optional[date] = None
    address: Optional[str] = None


class ProjectCreate(ProjectBase):
    """
    Schema for creating a new project.

    Note: created_by_user_id will be set by the service layer
    based on authentication context.
    """
    client_id: UUID
    category_id: UUID
    created_by_user_id: Optional[UUID] = None  # Will be set by service if not provided


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[date] = None
    address: Optional[str] = None
    category_id: Optional[UUID] = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: UUID
    client_id: UUID
    category_id: UUID
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDetailResponse(ProjectResponse):
    """
    Schema for detailed project response with relationships.

    Includes client, category, and creator information for full audit trail.
    """
    client: ClientResponse
    category: ProjectCategoryResponse
    created_by_name: Optional[str] = Field(None, description="Full name of the user who created this project")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_creator(cls, project):
        """Create response with creator's full name."""
        data = {
            **project.__dict__,
            "created_by_name": project.created_by.full_name if project.created_by else None,
            "client": project.client,
            "category": project.category
        }
        return cls(**data)
