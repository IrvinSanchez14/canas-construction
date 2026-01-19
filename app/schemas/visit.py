from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from app.models.visit import VisitStatus


class VisitItemSchema(BaseModel):
    """Schema for items collected during visit."""
    name: str
    description: Optional[str] = None
    quantity: float = Field(gt=0)
    unit_price: Decimal = Field(decimal_places=2)
    total_price: Optional[Decimal] = Field(None, decimal_places=2)

    model_config = ConfigDict(from_attributes=True)


class VisitBase(BaseModel):
    """Base schema for Visit."""
    title: str
    description: Optional[str] = None
    status: VisitStatus = VisitStatus.PLANNING
    visit_date: Optional[date] = None
    inspection_notes: Optional[str] = None
    estimated_materials_cost: Optional[Decimal] = Field(None, decimal_places=2)
    estimated_labor_cost: Optional[Decimal] = Field(None, decimal_places=2)
    estimated_total_cost: Optional[Decimal] = Field(None, decimal_places=2)
    images: Optional[List[str]] = None  # List of image URLs or paths
    attachments: Optional[List[str]] = None  # List of attachment URLs or paths
    visit_items: Optional[List[VisitItemSchema]] = None  # Items collected during visit

    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        """Validate maximum 10 images allowed per visit."""
        if v and len(v) > 10:
            raise ValueError("Maximum 10 images allowed per visit")
        return v

    @field_validator('attachments')
    @classmethod
    def validate_attachments(cls, v):
        """Validate maximum 10 attachments allowed per visit."""
        if v and len(v) > 10:
            raise ValueError("Maximum 10 attachments allowed per visit")
        return v

    @field_validator('images', 'attachments', mode='after')
    @classmethod
    def validate_total_media(cls, v, info):
        """Validate total media (images + attachments) does not exceed 10."""
        images = info.data.get('images') or []
        attachments = info.data.get('attachments') or []
        total_media = len(images) + len(attachments)
        if total_media > 10:
            raise ValueError("Maximum 10 photos/videos total allowed per visit (images + attachments)")
        return v


class VisitCreate(VisitBase):
    """Schema for creating a new visit."""
    project_id: UUID
    created_by_user_id: Optional[UUID] = None  # Will be set by service if not provided


class VisitUpdate(BaseModel):
    """Schema for updating a visit."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[VisitStatus] = None
    visit_date: Optional[date] = None
    inspection_notes: Optional[str] = None
    estimated_materials_cost: Optional[Decimal] = Field(None, decimal_places=2)
    estimated_labor_cost: Optional[Decimal] = Field(None, decimal_places=2)
    estimated_total_cost: Optional[Decimal] = Field(None, decimal_places=2)
    images: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    visit_items: Optional[List[VisitItemSchema]] = None
    edited_by_user_id: Optional[UUID] = None  # Will be set by service


class VisitResponse(VisitBase):
    """Schema for visit response."""
    id: UUID
    project_id: UUID
    created_by_user_id: Optional[UUID] = None
    edited_by_user_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VisitDetailResponse(VisitResponse):
    """
    Schema for detailed visit response with relationships.
    
    Includes project, creator, and editor information.
    """
    created_by_name: Optional[str] = Field(None, description="Full name of the user who created this visit")
    edited_by_name: Optional[str] = Field(None, description="Full name of the user who last edited this visit")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_details(cls, visit):
        """Create response with creator and editor names."""
        data = {
            **visit.__dict__,
            "created_by_name": visit.created_by.full_name if visit.created_by else None,
            "edited_by_name": visit.edited_by.full_name if visit.edited_by else None,
        }
        return cls(**data)


class VisitListResponse(BaseModel):
    """Schema for visit list response with pagination info."""
    visits: List[VisitDetailResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)
