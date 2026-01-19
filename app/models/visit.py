from sqlalchemy import Column, String, ForeignKey, Text, Enum, Numeric, Date, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum
from datetime import datetime


class VisitStatus(enum.Enum):
    """Enum for visit status in the construction workflow."""
    PLANNING = "planning"  # Initial visit planning stage
    IN_REVIEW = "in_review"  # Engineer reviewing the visit data
    APPROVED = "approved"  # Visit approved for planning phase
    INSPECTION_REQUIRED = "inspection_required"  # Additional inspection needed
    VISITED = "visited"  # Visit completed, all information gathered


class Visit(BaseModel):
    """
    Visit model for project inspections and information gathering.
    
    This table is the principal container of all the process about the project.
    Users create a visit to a project to add information, images, and details.
    Engineers in construction can review and change the status, edit information,
    or add new items and prices.
    """

    __tablename__ = "visits"

    # Basic information
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(VisitStatus, values_callable=lambda x: [e.value for e in x]),
        default=VisitStatus.PLANNING,
        nullable=False,
        index=True
    )

    # Visit details
    visit_date = Column(Date, nullable=True)
    inspection_notes = Column(Text, nullable=True)
    
    # Financial information collected during visit
    estimated_materials_cost = Column(Numeric(12, 2), nullable=True)
    estimated_labor_cost = Column(Numeric(12, 2), nullable=True)
    estimated_total_cost = Column(Numeric(12, 2), nullable=True)

    # Images and attachments (JSON array of file paths/URLs)
    images = Column(JSON, nullable=True)  # List of image URLs or paths
    attachments = Column(JSON, nullable=True)  # List of attachment URLs or paths

    # Items collected during visit (JSON array of items with prices)
    visit_items = Column(JSON, nullable=True)  # List of items: [{name, description, quantity, unit_price, total_price}]

    # Foreign key to project
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Foreign key to user who created this visit
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Foreign key to user who last edited this visit
    edited_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Review timestamp
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="visits")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    edited_by = relationship("User", foreign_keys=[edited_by_user_id])
    budget = relationship("Budget", back_populates="visit", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Visit(id={self.id}, title='{self.title}', status={self.status}, project_id={self.project_id})>"
