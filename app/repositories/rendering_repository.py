"""Rendering Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.models import Rendering, RenderingStatus
from app.models.rendering import RenderingImage, RenderingItem
from app.repositories.base import BaseRepository


class RenderingRepository(BaseRepository[Rendering]):
    """Repository for Rendering entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(Rendering, db)

    def get_by_id_with_details(self, rendering_id: UUID) -> Optional[Rendering]:
        """Get rendering by ID with images, items, visit, and budget eagerly loaded."""
        return (
            self.db.query(Rendering)
            .options(
                joinedload(Rendering.images),
                joinedload(Rendering.items),
                joinedload(Rendering.visit),
                joinedload(Rendering.budget)
            )
            .filter(Rendering.id == rendering_id)
            .first()
        )

    def get_by_visit(
        self,
        visit_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[RenderingStatus] = None,
        include_details: bool = True
    ) -> List[Rendering]:
        """
        Get all renderings for a specific visit.

        Args:
            visit_id: Visit ID filter
            skip: Pagination offset
            limit: Pagination limit
            status: Optional status filter
            include_details: Whether to eager load images and items
        """
        query = self.db.query(Rendering).filter(Rendering.visit_id == visit_id)

        if status:
            query = query.filter(Rendering.status == status)

        if include_details:
            query = query.options(
                joinedload(Rendering.images),
                joinedload(Rendering.items)
            )

        return query.order_by(Rendering.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_budget(
        self,
        budget_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Rendering]:
        """Get all renderings associated with a budget."""
        return (
            self.db.query(Rendering)
            .filter(Rendering.budget_id == budget_id)
            .options(
                joinedload(Rendering.images),
                joinedload(Rendering.items)
            )
            .order_by(Rendering.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_status(
        self,
        status: RenderingStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Rendering]:
        """Get all renderings with a specific status."""
        return (
            self.db.query(Rendering)
            .filter(Rendering.status == status)
            .options(
                joinedload(Rendering.visit),
                joinedload(Rendering.budget)
            )
            .order_by(Rendering.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_by_company(
        self,
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[RenderingStatus] = None,
        include_details: bool = True
    ) -> List[Rendering]:
        """
        Get all renderings for a company by joining through visits to projects to clients.

        Args:
            company_id: Company ID to filter by
            skip: Pagination offset
            limit: Pagination limit
            status: Optional status filter
            include_details: Whether to eager load images and items
        """
        from app.models import Visit, Project, Client

        query = (
            self.db.query(Rendering)
            .join(Rendering.visit)
            .join(Visit.project)
            .join(Project.client)
            .filter(Client.company_id == company_id)
        )

        if status:
            query = query.filter(Rendering.status == status)

        if include_details:
            query = query.options(
                joinedload(Rendering.images),
                joinedload(Rendering.items),
                joinedload(Rendering.visit),
                joinedload(Rendering.budget)
            )

        return query.order_by(Rendering.created_at.desc()).offset(skip).limit(limit).all()

    def count_by_visit(self, visit_id: UUID) -> int:
        """Count total renderings for a visit."""
        return self.db.query(Rendering).filter(Rendering.visit_id == visit_id).count()

    def count_by_status(self, status: RenderingStatus) -> int:
        """Count total renderings with a specific status."""
        return self.db.query(Rendering).filter(Rendering.status == status).count()


class RenderingImageRepository(BaseRepository[RenderingImage]):
    """Repository for RenderingImage entity."""

    def __init__(self, db: Session):
        super().__init__(RenderingImage, db)

    def get_by_rendering(
        self,
        rendering_id: UUID,
        image_type: Optional[str] = None
    ) -> List[RenderingImage]:
        """
        Get all images for a rendering.

        Args:
            rendering_id: Rendering ID filter
            image_type: Optional filter by type ('project' or 'material')
        """
        query = self.db.query(RenderingImage).filter(
            RenderingImage.rendering_id == rendering_id
        )

        if image_type:
            query = query.filter(RenderingImage.image_type == image_type)

        return query.order_by(RenderingImage.display_order).all()

    def get_max_display_order(self, rendering_id: UUID) -> int:
        """Get the maximum display order for images in a rendering."""
        from sqlalchemy import func
        result = (
            self.db.query(func.max(RenderingImage.display_order))
            .filter(RenderingImage.rendering_id == rendering_id)
            .scalar()
        )
        return result or 0

    def bulk_update_order(self, image_orders: List[tuple]) -> None:
        """
        Bulk update display orders for images.

        Args:
            image_orders: List of (image_id, new_order) tuples
        """
        for image_id, new_order in image_orders:
            self.db.query(RenderingImage).filter(
                RenderingImage.id == image_id
            ).update({"display_order": new_order})
        self.db.flush()


class RenderingItemRepository(BaseRepository[RenderingItem]):
    """Repository for RenderingItem entity."""

    def __init__(self, db: Session):
        super().__init__(RenderingItem, db)

    def get_by_rendering(
        self,
        rendering_id: UUID,
        category: Optional[str] = None
    ) -> List[RenderingItem]:
        """
        Get all items for a rendering.

        Args:
            rendering_id: Rendering ID filter
            category: Optional filter by category
        """
        query = self.db.query(RenderingItem).filter(
            RenderingItem.rendering_id == rendering_id
        )

        if category:
            query = query.filter(RenderingItem.category == category)

        return query.order_by(RenderingItem.order_index).all()

    def get_max_order_index(self, rendering_id: UUID) -> int:
        """Get the maximum order index for items in a rendering."""
        from sqlalchemy import func
        result = (
            self.db.query(func.max(RenderingItem.order_index))
            .filter(RenderingItem.rendering_id == rendering_id)
            .scalar()
        )
        return result or 0

    def get_categories(self, rendering_id: UUID) -> List[str]:
        """Get distinct categories for a rendering."""
        result = (
            self.db.query(RenderingItem.category)
            .filter(
                RenderingItem.rendering_id == rendering_id,
                RenderingItem.category.isnot(None)
            )
            .distinct()
            .all()
        )
        return [r[0] for r in result]

    def calculate_total(self, rendering_id: UUID) -> float:
        """Calculate total amount for all items in a rendering."""
        from sqlalchemy import func
        result = (
            self.db.query(func.sum(RenderingItem.total))
            .filter(RenderingItem.rendering_id == rendering_id)
            .scalar()
        )
        return float(result) if result else 0.0
