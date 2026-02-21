"""
Visit Attachment Model

Stores files (images and PDFs) attached to visits.
Users can upload attachments when viewing visit details.
"""

from sqlalchemy import Column, String, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class VisitAttachment(BaseModel):
    """
    Visit Attachment model for storing visit files.

    Supports images (JPEG, PNG, WebP, GIF) and PDF documents.
    Files are stored in Cloudflare R2 cloud storage.
    Maximum 20 attachments per visit.
    """

    __tablename__ = "visit_attachments"

    # File information
    filename = Column(String(255), nullable=False, comment="Original filename")
    file_url = Column(String(1000), nullable=False, comment="R2 storage URL")
    file_type = Column(String(50), nullable=False, comment="MIME type (image/jpeg, application/pdf, etc.)")
    file_size = Column(Integer, nullable=False, comment="File size in bytes")
    description = Column(Text, nullable=True, comment="Optional user description")

    # Foreign key to visit
    visit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Visit this attachment belongs to"
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
    visit = relationship("Visit", back_populates="visit_attachments")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])

    def __repr__(self):
        return f"<VisitAttachment(id={self.id}, filename='{self.filename}', visit_id={self.visit_id})>"
