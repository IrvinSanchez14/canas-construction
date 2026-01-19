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
    
    Each visit can have one budget that contains line items (products/services).
    Budget items can reference catalog items (for reusable products) or be custom items.
    When budget is accepted, the project status changes to APPROVED.
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

    # Financial (calculated from items, but stored for performance)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)

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
    budget_items = relationship(
        "BudgetItem",
        back_populates="budget",
        cascade="all, delete-orphan",
        order_by="BudgetItem.order_index"
    )
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id])

    def __repr__(self):
        return f"<Budget(id={self.id}, title='{self.title}', status={self.status}, visit_id={self.visit_id})>"


class BudgetItem(BaseModel):
    """
    Budget Item model for individual line items in a budget.
    
    Each item can optionally reference a catalog item (for reusable products/services)
    but stores the actual price used (prices change over time).
    Items can also be custom (project-specific) without catalog reference.
    """

    __tablename__ = "budget_items"

    # Line item details
    section_name = Column(String(255), nullable=True, index=True)  # e.g., "PROVISIONALS", "DEMO", "ELECTRICAL"
    description = Column(Text, nullable=False)
    unit = Column(String(50), nullable=True)  # "each", "sq ft", "ft", "hr", "day", etc.
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)  # Actual price used (may differ from catalog)
    subtotal = Column(Numeric(12, 2), nullable=False)  # quantity * unit_price

    # Ordering within budget
    order_index = Column(Integer, nullable=False, default=0)

    # Optional: Reference to catalog item (if item came from catalog)
    catalog_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Reference to catalog item if this was added from catalog"
    )

    # Foreign key to budget
    budget_id = Column(
        UUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    budget = relationship("Budget", back_populates="budget_items")
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])

    def __repr__(self):
        return f"<BudgetItem(id={self.id}, description='{self.description[:50]}...', budget_id={self.budget_id})>"
