from sqlalchemy import Column, String, ForeignKey, Text, Numeric, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class BudgetCategory(BaseModel):
    """
    Budget Category model for grouping budget items.

    Each budget can have many categories (e.g., "Demolition", "Electrical", "Plumbing").
    Each category contains many budget items and can have up to 3 images.
    """

    __tablename__ = "budget_categories"

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    images = Column(JSON, nullable=True)  # Array of image URLs, max 3
    order_index = Column(Integer, nullable=False, default=0)
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)

    # Foreign key to budget
    budget_id = Column(
        UUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    budget = relationship("Budget", back_populates="budget_categories")
    budget_items = relationship(
        "BudgetItem",
        back_populates="budget_category",
        cascade="all, delete-orphan",
        order_by="BudgetItem.order_index"
    )

    # One-to-one: internal profit breakdown
    category_profit = relationship(
        "CategoryProfit",
        back_populates="budget_category",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<BudgetCategory(id={self.id}, name='{self.name}', budget_id={self.budget_id})>"
