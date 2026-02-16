"""
Category Profit Model

Internal cost breakdown per budget category.
Tracks provider cost, delivery cost, and profit markup.
The calculated total_price feeds into the client-facing budget.
"""

from sqlalchemy import Column, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class CategoryProfit(BaseModel):
    """
    Category Profit model for internal cost tracking.

    One-to-one relationship with BudgetCategory.
    Stores: provider_price + delivery_cost + profit markup = total_price
    total_price is what the client pays (synced to BudgetCategory.subtotal).
    """

    __tablename__ = "category_profits"

    # Foreign key to budget category (one-to-one via unique constraint)
    budget_category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Cost breakdown
    provider_price = Column(Numeric(12, 2), nullable=False, default=0)
    delivery_cost = Column(Numeric(12, 2), nullable=False, default=0)
    profit_percentage = Column(Numeric(5, 2), nullable=False, default=0)

    # Calculated: (provider_price + delivery_cost) * (1 + profit_percentage/100)
    total_price = Column(Numeric(12, 2), nullable=False, default=0)

    # Audit: who set this up
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Relationships
    budget_category = relationship(
        "BudgetCategory",
        back_populates="category_profit",
        uselist=False
    )
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self):
        return (
            f"<CategoryProfit(id={self.id}, "
            f"category_id={self.budget_category_id}, "
            f"total_price={self.total_price})>"
        )
