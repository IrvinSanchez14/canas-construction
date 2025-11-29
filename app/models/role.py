from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Role(BaseModel):
    """Role model - each company can define its own roles."""

    __tablename__ = "roles"

    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Foreign key to company for multi-tenant isolation
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    company = relationship("Company", back_populates="roles")
    users = relationship("User", secondary="user_roles", back_populates="roles")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}', company_id={self.company_id})>"
