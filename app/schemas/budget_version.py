from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID


class BudgetVersionResponse(BaseModel):
    """Schema for budget version response."""
    id: UUID
    budget_id: UUID
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


class BudgetVersionListResponse(BaseModel):
    """Schema for budget version list response with pagination."""
    versions: List[BudgetVersionResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)
