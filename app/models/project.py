from sqlalchemy import Column, String, ForeignKey, Text, Enum, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class ProjectStatus(enum.Enum):
    """Enum for project status."""
    LEAD = "lead"
    QUOTED = "quoted"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class Project(BaseModel):
    """
    Project model for multi-tenant CRM.

    Represents construction projects for clients.
    Each project belongs to a client and has a category.
    """

    __tablename__ = "projects"

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(ProjectStatus),
        default=ProjectStatus.LEAD,
        nullable=False,
        index=True
    )

    # Financial information
    estimated_budget = Column(Numeric(12, 2), nullable=True)
    actual_cost = Column(Numeric(12, 2), nullable=True)

    # Dates
    start_date = Column(Date, nullable=True)
    estimated_completion_date = Column(Date, nullable=True)
    actual_completion_date = Column(Date, nullable=True)

    # Location
    address = Column(String(500), nullable=True)

    # Foreign key to client
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Foreign key to project category
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Foreign key to user who created this project (audit trail)
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # NULL if user is deleted
        index=True
    )

    # Relationships
    client = relationship("Client", back_populates="projects")
    category = relationship("ProjectCategory", back_populates="projects")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', status={self.status}, client_id={self.client_id})>"
