from sqlalchemy import Column, String, ForeignKey, Text, Enum, Numeric, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class BudgetStatus(enum.Enum):
    """Enum for budget status in the construction workflow."""
    DRAFT = "draft"  # Budget being created/edited
    PENDING_APPROVAL = "pending_approval"  # Budget submitted for client approval
    ACCEPTED = "accepted"  # Budget accepted by client
    REJECTED = "rejected"  # Budget rejected by client
    REVISED = "revised"  # Budget revised after rejection


class Budget(BaseModel):
    """
    Budget model for project cost breakdowns.

    Structure: Budget → Categories → Items
    Each visit can have one budget containing categories with line items.
    Budget versions are stored as JSON snapshots for historical reference.
    """

    __tablename__ = "budgets"

    # Basic information
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(BudgetStatus, values_callable=lambda x: [e.value for e in x]),
        default=BudgetStatus.DRAFT,
        nullable=False,
        index=True
    )

    # Financial (calculated from categories/items, stored for performance)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)

    # Version tracking
    current_version = Column(Integer, nullable=False, default=0)

    # Foreign key to visit (one-to-one relationship)
    visit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visits.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Acceptance tracking
    accepted_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    accepted_at = Column(DateTime, nullable=True)

    # Relationships
    visit = relationship("Visit", back_populates="budget", uselist=False)
    budget_categories = relationship(
        "BudgetCategory",
        back_populates="budget",
        cascade="all, delete-orphan",
        order_by="BudgetCategory.order_index"
    )
    versions = relationship(
        "BudgetVersion",
        back_populates="budget",
        cascade="all, delete-orphan",
        order_by="BudgetVersion.version_number"
    )
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id])

    def __repr__(self):
        return f"<Budget(id={self.id}, title='{self.title}', status={self.status}, visit_id={self.visit_id})>"


class BudgetItem(BaseModel):
    """
    Budget Item model for individual line items within a budget category.

    Each item belongs to a category. Items can optionally reference a catalog item
    for reusable products/services, but stores the actual price used.
    """

    __tablename__ = "budget_items"

    # Line item details
    description = Column(Text, nullable=False)
    unit = Column(String(50), nullable=True)  # "each", "sq ft", "ft", "hr", "day", etc.
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)  # quantity * unit_price

    # Ordering within category
    order_index = Column(Integer, nullable=False, default=0)

    # Optional: Reference to catalog item
    catalog_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Foreign key to budget category
    budget_category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    budget_category = relationship("BudgetCategory", back_populates="budget_items")
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])

    def __repr__(self):
        return f"<BudgetItem(id={self.id}, description='{self.description[:50]}...', category_id={self.budget_category_id})>"
