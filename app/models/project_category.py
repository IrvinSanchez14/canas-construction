from sqlalchemy import Column, String, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ProjectCategory(BaseModel):
    """
    Project Category model for multi-tenant CRM.

    Each company can define their own project categories
    (e.g., Kitchen, Bathroom, Outside, Other).
    This allows flexibility for different types of construction companies.
    """

    __tablename__ = "project_categories"

    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Foreign key to company for multi-tenant isolation
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    company = relationship("Company", back_populates="project_categories")
    projects = relationship("Project", back_populates="category")

    def __repr__(self):
        return f"<ProjectCategory(id={self.id}, name='{self.name}', company_id={self.company_id})>"
