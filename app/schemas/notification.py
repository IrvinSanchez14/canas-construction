from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# Notification Settings Schemas
class NotificationSettingsBase(BaseModel):
    enabled: bool = True


class NotificationSettingsCreate(NotificationSettingsBase):
    company_id: UUID


class NotificationSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None


class NotificationSettingsResponse(NotificationSettingsBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime


# Notification Recipient Schemas
class NotificationRecipientBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class NotificationRecipientCreate(NotificationRecipientBase):
    pass


class NotificationRecipientUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationRecipientResponse(NotificationRecipientBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    notification_setting_id: UUID
    is_active: bool
    created_at: datetime


# Notification Event Schema (internal use)
class NotificationEvent(BaseModel):
    """Schema for notification events."""
    
    event_type: str  # e.g., "client.created"
    entity_type: str  # e.g., "Client"
    entity_id: UUID
    entity_name: str
    company_id: UUID
    created_by: Optional[str] = None
    details: Optional[dict] = None
