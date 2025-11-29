from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from app.schemas.role import RoleResponse


class UserBase(BaseModel):
    """Base schema for User."""
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str
    company_id: UUID
    role_ids: Optional[List[UUID]] = []


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    password: Optional[str] = None
    role_ids: Optional[List[UUID]] = None


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    company_id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    roles: List[RoleResponse] = []

    model_config = ConfigDict(from_attributes=True)
