from sqlalchemy import Column, String, ForeignKey, Text, Boolean, Numeric, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class UnitType(enum.Enum):
    """Enum for unit types in catalog items."""
    POUND = "lb"  # Pounds
    SQUARE_FOOT = "sq ft"  # Square feet
    FOOT = "ft"  # Linear feet
    CUBIC_YARD = "cu yd"  # Cubic yards
    EACH = "each"  # Each (individual items)
    HOUR = "hr"  # Hours (for labor)
    DAY = "day"  # Days


class CatalogItem(BaseModel):
    """
    Catalog Item model for multi-tenant CRM.

    Stores materials, labor, and other items that can be used
    in project cost breakdowns. Each item tracks the user who created it.
    """

    __tablename__ = "catalog_items"

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    unity = Column(
        Enum(UnitType),
        nullable=False,
        index=True
    )
    price_base = Column(
        Numeric(12, 2),
        nullable=False,
        comment="Default/base price when item is created"
    )
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Foreign key to company for multi-tenant isolation
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Foreign key to user who created this item (audit trail)
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # NULL if user is deleted
        index=True
    )

    # Relationships
    company = relationship("Company", back_populates="catalog_items")
    created_by = relationship("User", back_populates="created_catalog_items", foreign_keys=[created_by_user_id])

    def __repr__(self):
        return f"<CatalogItem(id={self.id}, name='{self.name}', unity={self.unity}, company_id={self.company_id})>"
