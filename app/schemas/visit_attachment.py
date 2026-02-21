"""
Visit Attachment Schemas

Pydantic schemas for visit attachment API requests and responses.
"""

from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class VisitAttachmentBase(BaseModel):
    """Base schema for visit attachment."""
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")


class VisitAttachmentCreate(VisitAttachmentBase):
    """Schema for creating a visit attachment (used internally after upload)."""
    filename: str = Field(..., max_length=255, description="Original filename")
    file_url: str = Field(..., max_length=1000, description="R2 storage URL")
    file_type: str = Field(..., max_length=50, description="MIME type")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    visit_id: UUID = Field(..., description="Visit ID")
    uploaded_by_user_id: Optional[UUID] = Field(None, description="User who uploaded")


class VisitAttachmentUpdate(BaseModel):
    """Schema for updating attachment (only description is editable)."""
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")


class VisitAttachmentResponse(VisitAttachmentBase):
    """Schema for visit attachment response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Attachment ID")
    filename: str = Field(..., description="Original filename")
    file_url: str = Field(..., description="Public URL")
    file_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="File size in bytes")
    visit_id: UUID = Field(..., description="Visit ID")
    uploaded_by_user_id: Optional[UUID] = Field(None, description="User who uploaded")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Computed fields for user info (populated by service)
    uploaded_by_name: Optional[str] = Field(None, description="Name of user who uploaded")


class VisitAttachmentListResponse(BaseModel):
    """Schema for listing attachments."""
    attachments: list[VisitAttachmentResponse] = Field(..., description="List of attachments")
    total: int = Field(..., description="Total count")
    max_allowed: int = Field(default=20, description="Maximum attachments per visit")
