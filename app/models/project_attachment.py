"""
Project Attachment Model

Stores files (images and PDFs) attached to projects.
Users can upload attachments when editing projects.
"""

from sqlalchemy import Column, String, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ProjectAttachment(BaseModel):
    """
    Project Attachment model for storing project files.
    
    Supports images (JPEG, PNG, WebP, GIF) and PDF documents.
    Files are stored in Cloudflare R2 cloud storage.
    Maximum 20 attachments per project.
    """

    __tablename__ = "project_attachments"

    # File information
    filename = Column(String(255), nullable=False, comment="Original filename")
    file_url = Column(String(1000), nullable=False, comment="R2 storage URL")
    file_type = Column(String(50), nullable=False, comment="MIME type (image/jpeg, application/pdf, etc.)")
    file_size = Column(Integer, nullable=False, comment="File size in bytes")
    description = Column(Text, nullable=True, comment="Optional user description")

    # Foreign key to project
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Project this attachment belongs to"
    )

    # Foreign key to user who uploaded
    uploaded_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who uploaded this attachment"
    )

    # Relationships
    project = relationship("Project", back_populates="attachments")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])

    def __repr__(self):
        return f"<ProjectAttachment(id={self.id}, filename='{self.filename}', project_id={self.project_id})>"
