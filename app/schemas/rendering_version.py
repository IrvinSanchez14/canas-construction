from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class RenderingVersionResponse(BaseModel):
    """Schema for rendering version response."""
    id: UUID
    rendering_id: UUID
    version_number: int
    snapshot: dict
    notes: Optional[str] = None
    created_by_user_id: Optional[UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_details(cls, version):
        data = {
            **version.__dict__,
            "created_by_name": version.created_by.full_name if version.created_by else None,
        }
        return cls(**data)


class RenderingVersionListResponse(BaseModel):
    """Schema for rendering version list response with pagination."""
    versions: List[RenderingVersionResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)
