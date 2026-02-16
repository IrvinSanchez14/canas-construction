from sqlalchemy import Column, ForeignKey, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class BudgetVersion(BaseModel):
    """
    Budget Version model for storing historical snapshots of budgets.

    Each time a budget is modified, a snapshot is saved so the admin
    can review previous versions of the budget for any project.
    """

    __tablename__ = "budget_versions"

    budget_id = Column(
        UUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)  # Full budget data at that point in time
    notes = Column(Text, nullable=True)

    # Who created this version
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Relationships
    budget = relationship("Budget", back_populates="versions")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self):
        return f"<BudgetVersion(id={self.id}, budget_id={self.budget_id}, version={self.version_number})>"
