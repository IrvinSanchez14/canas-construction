from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from app.models.rendering import RenderingStatus


# ============== Rendering Image Schemas ==============

class RenderingImageBase(BaseModel):
    """Base schema for RenderingImage."""
    image_url: str = Field(..., max_length=500)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: int = Field(default=0, ge=0)
    is_full_page: bool = False
    image_type: str = Field(default='project', pattern='^(project|material)$')


class RenderingImageCreate(RenderingImageBase):
    """Schema for creating a rendering image."""
    pass


class RenderingImageUpdate(BaseModel):
    """Schema for updating a rendering image."""
    image_url: Optional[str] = Field(None, max_length=500)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_full_page: Optional[bool] = None
    image_type: Optional[str] = Field(None, pattern='^(project|material)$')


class RenderingImageResponse(RenderingImageBase):
    """Schema for rendering image response."""
    id: UUID
    rendering_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Rendering Item Schemas ==============

class RenderingItemBase(BaseModel):
    """Base schema for RenderingItem."""
    category: Optional[str] = Field(None, max_length=255)
    name: str = Field(..., max_length=255)
    specifications: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    material_image_url: Optional[str] = Field(None, max_length=500)
    product_image_url: Optional[str] = Field(None, max_length=500)
    quantity: Decimal = Field(default=Decimal('1'), ge=0)
    unit: Optional[str] = Field(None, max_length=50)
    unit_price: Decimal = Field(default=Decimal('0'), ge=0)
    subtotal: Decimal = Field(default=Decimal('0'), ge=0)
    tax: Optional[Decimal] = Field(None, ge=0)
    total: Decimal = Field(default=Decimal('0'), ge=0)
    disclaimer: Optional[str] = None
    is_material_sample: bool = False
    show_in_materials_page: bool = False
    show_in_details_page: bool = True
    order_index: int = Field(default=0, ge=0)


class RenderingItemCreate(RenderingItemBase):
    """Schema for creating a rendering item."""
    budget_item_id: Optional[UUID] = None


class RenderingItemUpdate(BaseModel):
    """Schema for updating a rendering item."""
    category: Optional[str] = Field(None, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    specifications: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    material_image_url: Optional[str] = Field(None, max_length=500)
    product_image_url: Optional[str] = Field(None, max_length=500)
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=50)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    subtotal: Optional[Decimal] = Field(None, ge=0)
    tax: Optional[Decimal] = Field(None, ge=0)
    total: Optional[Decimal] = Field(None, ge=0)
    disclaimer: Optional[str] = None
    is_material_sample: Optional[bool] = None
    show_in_materials_page: Optional[bool] = None
    show_in_details_page: Optional[bool] = None
    order_index: Optional[int] = Field(None, ge=0)


class RenderingItemResponse(RenderingItemBase):
    """Schema for rendering item response."""
    id: UUID
    rendering_id: UUID
    budget_item_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Rendering Schemas ==============

class RenderingBase(BaseModel):
    """Base schema for Rendering."""
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    notes: Optional[str] = None
    status: RenderingStatus = RenderingStatus.DRAFT


class RenderingCreate(RenderingBase):
    """Schema for creating a rendering."""
    project_id: Optional[UUID] = None
    visit_id: Optional[UUID] = None
    budget_id: Optional[UUID] = None
    expiration_date: Optional[date] = None


class RenderingUpdate(BaseModel):
    """Schema for updating a rendering."""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    notes: Optional[str] = None
    expiration_date: Optional[date] = None
    status: Optional[RenderingStatus] = None
    project_id: Optional[UUID] = None
    visit_id: Optional[UUID] = None
    budget_id: Optional[UUID] = None
    sent_to_email: Optional[str] = Field(None, max_length=255)
    approved_by_client_name: Optional[str] = Field(None, max_length=255)


class RenderingResponse(RenderingBase):
    """Schema for rendering response."""
    id: UUID
    total_amount: Decimal
    project_id: Optional[UUID] = None
    visit_id: Optional[UUID] = None
    budget_id: Optional[UUID] = None
    expiration_date: Optional[date] = None
    sent_at: Optional[datetime] = None
    sent_to_email: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by_client_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RenderingDetailResponse(RenderingResponse):
    """
    Schema for detailed rendering response with relationships.

    Includes images, items, and related visit/budget information.
    """
    images: List[RenderingImageResponse] = []
    items: List[RenderingItemResponse] = []
    visit_title: Optional[str] = Field(None, description="Title of the related visit")
    budget_title: Optional[str] = Field(None, description="Title of the related budget")
    project_name: Optional[str] = Field(None, description="Name of the project (via visit)")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_details(cls, rendering):
        """Create response with visit and budget details."""
        data = {
            **rendering.__dict__,
            "images": [RenderingImageResponse.model_validate(img) for img in rendering.images],
            "items": [RenderingItemResponse.model_validate(item) for item in rendering.items],
            "visit_title": rendering.visit.title if rendering.visit else None,
            "budget_title": rendering.budget.title if rendering.budget else None,
            "project_name": rendering.project.name if rendering.project else (rendering.visit.project.name if rendering.visit and rendering.visit.project else None),
        }
        return cls(**data)


class RenderingListResponse(BaseModel):
    """Schema for rendering list response with pagination info."""
    renderings: List[RenderingResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)


# ============== Bulk Operations ==============

class ReorderImagesRequest(BaseModel):
    """Schema for reordering rendering images."""
    image_ids: List[UUID] = Field(..., description="Ordered list of image IDs")

    @field_validator('image_ids')
    @classmethod
    def validate_image_ids(cls, v):
        """Validate at least one image ID provided."""
        if not v:
            raise ValueError("At least one image ID must be provided")
        if len(v) != len(set(v)):
            raise ValueError("Duplicate image IDs not allowed")
        return v


class ImportBudgetItemsRequest(BaseModel):
    """Schema for importing budget items into a rendering."""
    budget_id: UUID
    item_ids: Optional[List[UUID]] = Field(
        None,
        description="Specific budget item IDs to import. If not provided, imports all items."
    )


class SendRenderingRequest(BaseModel):
    """Schema for sending a rendering to client."""
    email: str = Field(..., max_length=255)
    message: Optional[str] = Field(None, description="Optional message to include in email")
