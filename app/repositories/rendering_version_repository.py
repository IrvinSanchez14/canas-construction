"""RenderingVersion Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.models.rendering_version import RenderingVersion
from app.repositories.base import BaseRepository


class RenderingVersionRepository(BaseRepository[RenderingVersion]):
    """Repository for RenderingVersion entity."""

    def __init__(self, db: Session):
        super().__init__(RenderingVersion, db)

    def get_by_rendering(
        self,
        rendering_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[RenderingVersion]:
        """Get all versions for a rendering ordered by version number descending."""
        return (
            self.db.query(RenderingVersion)
            .options(joinedload(RenderingVersion.created_by))
            .filter(RenderingVersion.rendering_id == rendering_id)
            .order_by(RenderingVersion.version_number.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_latest_version_number(self, rendering_id: UUID) -> int:
        """Get the latest version number for a rendering."""
        result = (
            self.db.query(RenderingVersion.version_number)
            .filter(RenderingVersion.rendering_id == rendering_id)
            .order_by(RenderingVersion.version_number.desc())
            .first()
        )
        return result[0] if result else 0

    def count_by_rendering(self, rendering_id: UUID) -> int:
        """Count total versions for a rendering."""
        return (
            self.db.query(RenderingVersion)
            .filter(RenderingVersion.rendering_id == rendering_id)
            .count()
        )

    def get_by_id_with_details(self, version_id: UUID) -> Optional[RenderingVersion]:
        """Get version by ID with creator eagerly loaded."""
        return (
            self.db.query(RenderingVersion)
            .options(joinedload(RenderingVersion.created_by))
            .filter(RenderingVersion.id == version_id)
            .first()
        )
