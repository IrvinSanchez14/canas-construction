from sqlalchemy import Column, String, ForeignKey, Text, Enum, Numeric, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class ChangeOrderStatus(enum.Enum):
    """Enum for change order status."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED = "applied"  # Applied to budget, new version created


class ChangeOrder(BaseModel):
    """
    Change Order model for mid-project modifications.

    A change order is created when extra work or modifications arise during
    an active project. It links to a project, contains line items, and
    when applied finds the project's budget and creates a new version.
    """

    __tablename__ = "change_orders"

    # Basic information
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    observations = Column(JSON, nullable=True)  # Array of observation strings
    order_number = Column(Integer, nullable=False, default=1)
    status = Column(
        Enum(ChangeOrderStatus, values_callable=lambda x: [e.value for e in x]),
        default=ChangeOrderStatus.DRAFT,
        nullable=False,
        index=True
    )

    # Financial (calculated from items)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)

    # Foreign key to project
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
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

    # Applied tracking (when change order is applied to budget)
    applied_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    applied_at = Column(DateTime, nullable=True)

    # Who created this change order
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Relationships
    project = relationship("Project", back_populates="change_orders")
    change_order_items = relationship(
        "ChangeOrderItem",
        back_populates="change_order",
        cascade="all, delete-orphan",
        order_by="ChangeOrderItem.order_index"
    )
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id])
    applied_by = relationship("User", foreign_keys=[applied_by_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self):
        return f"<ChangeOrder(id={self.id}, title='{self.title}', status={self.status}, project_id={self.project_id})>"


class ChangeOrderItem(BaseModel):
    """
    Change Order Item model for individual line items.

    Each item represents work to be added or modified in the project.
    """

    __tablename__ = "change_order_items"

    # Line item details
    item_code = Column(String(20), nullable=True)  # e.g., "0131", "0141"
    description = Column(Text, nullable=False)
    unit = Column(String(50), nullable=True)  # "each", "sq ft", "ft", etc.
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)  # quantity * unit_price

    # Ordering
    order_index = Column(Integer, nullable=False, default=0)

    # Foreign key to change order
    change_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("change_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    change_order = relationship("ChangeOrder", back_populates="change_order_items")

    def __repr__(self):
        return f"<ChangeOrderItem(id={self.id}, description='{self.description[:50]}...', change_order_id={self.change_order_id})>"
