from sqlalchemy import Column, ForeignKey, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class RenderingVersion(BaseModel):
    """
    Rendering Version model for storing historical snapshots of renderings.

    Each time a rendering is modified, a snapshot is saved so the admin
    can review previous versions of the rendering for any project.
    """

    __tablename__ = "rendering_versions"

    rendering_id = Column(
        UUID(as_uuid=True),
        ForeignKey("renderings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)  # Full rendering data at that point in time
    notes = Column(Text, nullable=True)

    # Who created this version
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Relationships
    rendering = relationship("Rendering", back_populates="versions")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self):
        return f"<RenderingVersion(id={self.id}, rendering_id={self.rendering_id}, version={self.version_number})>"
